---
name: api-security
description: >
  Guards JWT para endpoints FastAPI, decorador de permisos por rol (RBAC),
  middleware de rate limiting, configuracion CORS, rotacion de refresh tokens
  con blacklist, y hashing seguro de passwords.
  Trigger: cuando se trabaje en autenticacion, autorizacion, JWT, rate limiting o seguridad.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o modificar cualquier endpoint que requiera autenticación
- Al implementar roles de usuario (alumno, docente, admin)
- Al configurar el flujo de refresh token rotation
- Al agregar rate limiting a rutas de la API
- Al revisar headers CORS, password hashing, o cualquier lógica de seguridad
- Al definir dependencias de FastAPI que inyecten el usuario actual

## Patrones Críticos

### 1. Dependencia get_current_user con Validacion JWT

La dependencia valida firma, expiración y blacklist en cada request.
Se inyecta con `Depends(get_current_user)` en cualquier endpoint protegido.

```python
# core/security/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import settings
from app.infrastructure.redis.token_blacklist import is_token_blacklisted
from app.infrastructure.redis.deps import get_redis
from app.schemas.auth import TokenPayload
from redis.asyncio import Redis

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    redis: Redis = Depends(get_redis),
) -> TokenPayload:
    """Valida JWT: firma, expiración y blacklist. Lanza 401 si falla."""
    token = credentials.credentials
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,          # nunca hardcoded, viene de env
            algorithms=[settings.JWT_ALGORITHM],
        )
        jti: str | None = payload.get("jti")
        if jti is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    # Verificar que el token no fue blacklisteado (ej: tras refresh rotation)
    if await is_token_blacklisted(redis, jti):
        raise credentials_exc

    return TokenPayload(**payload)
```

### 2. RequireRole: Dependency Factory para RBAC

Genera una dependencia que verifica el rol del usuario autenticado.
Se encadena sobre `get_current_user` sin duplicar lógica de auth.

```python
# core/security/rbac.py

from fastapi import Depends, HTTPException, status
from app.core.security.dependencies import get_current_user
from app.schemas.auth import TokenPayload

class RequireRole:
    """
    Dependency factory para RBAC.
    Uso: Depends(RequireRole("admin")) o Depends(RequireRole("docente", "admin"))
    """
    def __init__(self, *allowed_roles: str) -> None:
        self.allowed_roles = set(allowed_roles)

    async def __call__(
        self,
        current_user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{current_user.role}' no tiene acceso a este recurso.",
            )
        return current_user

# Instancias reutilizables (evita instanciar en cada endpoint)
require_admin     = RequireRole("admin")
require_docente = RequireRole("docente", "admin")
require_alumno   = RequireRole("alumno", "docente", "admin")

# Uso en un endpoint:
# @router.get("/admin/users")
# async def list_users(user: TokenPayload = Depends(require_admin)):
#     ...
```

### 3. Refresh Token Rotation: Validar → Generar → Blacklistear

El flujo completo en un solo servicio. El token viejo se blacklistea inmediatamente
para prevenir reutilización (token reuse attack).

```python
# services/auth_service.py

import uuid, time
from jose import jwt, JWTError
from app.core.config import settings
from app.infrastructure.redis.token_blacklist import blacklist_token, is_token_blacklisted
from app.schemas.auth import TokenPair

async def rotate_refresh_token(
    refresh_token: str,
    redis,
) -> TokenPair:
    """
    Valida el refresh token, genera un par nuevo y blacklistea el viejo.
    Lanza ValueError si el token es invalido o ya fue usado.
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("Refresh token invalido") from exc

    jti: str = payload["jti"]
    exp: int = payload["exp"]
    user_id: str = payload["sub"]
    role: str = payload["role"]

    # Prevenir reutilizacion del mismo refresh token
    if await is_token_blacklisted(redis, jti):
        raise ValueError("Refresh token ya fue utilizado (posible ataque de replay)")

    # Blacklistear el token viejo ANTES de emitir el nuevo
    await blacklist_token(redis, jti, exp)

    # Generar par nuevo
    new_access  = _create_access_token(user_id, role)
    new_refresh = _create_refresh_token(user_id, role)
    return TokenPair(access_token=new_access, refresh_token=new_refresh)

def _create_access_token(user_id: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def _create_refresh_token(user_id: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + settings.REFRESH_TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### 4. Decorador de Rate Limiting con Redis Sliding Window

Envuelve cualquier endpoint con rate limit configurado.
Usa `X-RateLimit-Remaining` y `X-RateLimit-Reset` en los headers de respuesta.

```python
# core/security/rate_limit.py

import time
from functools import wraps
from fastapi import HTTPException, Request, status
from app.infrastructure.redis.rate_limiter import check_rate_limit

def rate_limit(limit: int, window_seconds: int, endpoint_key: str):
    """
    Decorador de rate limiting basado en Redis sliding window.
    Uso:
        @rate_limit(limit=100, window_seconds=60, endpoint_key="api_general")
        async def my_endpoint(request: Request, ...):
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Extraer user_id del state (puesto por get_current_user)
            user_id: str = getattr(request.state, "user_id", request.client.host)
            redis = request.state.redis

            key = f"rl:{endpoint_key}:{user_id}"
            allowed, remaining = await check_rate_limit(
                redis, key, limit, window_seconds
            )
            if not allowed:
                reset_at = int(time.time()) + window_seconds
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit excedido. Intentá de nuevo más tarde.",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                        "Retry-After": str(window_seconds),
                    },
                )

            response = await func(request, *args, **kwargs)
            # Agregar headers informativos en respuestas exitosas
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        return wrapper
    return decorator

# Uso:
# @router.post("/tutor/message")
# @rate_limit(limit=30, window_seconds=3600, endpoint_key="tutor")  # key debe incluir exercise_id: rl:tutor:{user_id}:{exercise_id}
# async def send_message(request: Request, body: MessageBody):
#     ...
```

## Anti-patrones

### DON'T: JWT secret hardcodeado en el código

```python
# MAL — secreto expuesto en el repositorio
payload = jwt.decode(token, "mi_secreto_super_seguro_123", algorithms=["HS256"])
```

```python
# BIEN — siempre desde variables de entorno via settings
from app.core.config import settings
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
```

### DON'T: Endpoint sin verificacion de rol (cualquier usuario autenticado accede)

```python
# MAL — un student puede ver el panel de evaluación de profesores
@router.get("/evaluations/summary")
async def get_summary(user: TokenPayload = Depends(get_current_user)):
    return await evaluation_service.get_all()
```

```python
# BIEN — restringir explicitamente por rol
from app.core.security.rbac import require_docente

@router.get("/evaluations/summary")
async def get_summary(user: TokenPayload = Depends(require_docente)):
    return await evaluation_service.get_all()
```

### DON'T: No blacklistear el refresh token viejo al rotar

```python
# MAL — el token viejo sigue siendo válido, abre vector de replay attack
async def rotate_refresh_token(refresh_token: str) -> TokenPair:
    payload = jwt.decode(refresh_token, settings.SECRET_KEY, ...)
    return TokenPair(
        access_token=_create_access_token(payload["sub"], payload["role"]),
        refresh_token=_create_refresh_token(payload["sub"], payload["role"]),
    )
```

```python
# BIEN — blacklistear el viejo ANTES de devolver el nuevo
await blacklist_token(redis, payload["jti"], payload["exp"])
return TokenPair(...)
```

### DON'T: Rate limiting solo en memoria (se resetea en cada restart)

```python
# MAL — contador en memoria: al reiniciar el server, se borra
_counters: dict[str, int] = {}

async def check_limit(user_id: str) -> bool:
    _counters[user_id] = _counters.get(user_id, 0) + 1
    return _counters[user_id] <= 30
```

```python
# BIEN — siempre en Redis con sliding window (persistente entre restarts)
allowed, remaining = await check_rate_limit(
    redis, user_id, "tutor", limit=30, window_seconds=3600
)
```

## Notas Adicionales

### Almacenamiento de Tokens

- **Access token**: Zustand memory (no `localStorage`, no `sessionStorage`) — se pierde al recargar la página intencionalmente.
- **Refresh token**: `httpOnly` cookie — inaccesible desde JavaScript, protege contra XSS.

### Asignación de Roles

El campo `role` **nunca** se acepta en el body de registro. El rol por defecto es `alumno`. Solo un administrador puede asignar roles distintos mediante un endpoint dedicado (`PATCH /api/v1/admin/users/{id}/role`).

## Checklist

- [ ] `SECRET_KEY` viene de `settings` (env var), nunca hardcodeada
- [ ] Todos los endpoints protegidos usan `Depends(get_current_user)` o `Depends(require_*)
- [ ] Los endpoints de profesor/admin tienen `Depends(require_docente)` o `Depends(require_admin)`
- [ ] El JTI se incluye en el payload de todos los tokens emitidos
- [ ] La blacklist se verifica en `get_current_user` antes de retornar el payload
- [ ] Refresh token rotation blacklistea el token viejo ANTES de emitir el nuevo
- [ ] El rate limiter usa Redis sliding window (no in-memory)
- [ ] Tutor endpoint: `limit=30, window_seconds=3600`, key incluye `exercise_id` → `rl:tutor:{user_id}:{exercise_id}`
- [ ] API general: `limit=100, window_seconds=60`
- [ ] Los headers `X-RateLimit-*` y `Retry-After` se incluyen en las respuestas 429
- [ ] CORS configurado con `allow_origins` explícito (no `"*"` en produccion)
- [ ] Passwords hasheados con `bcrypt` (factor de costo >= 12), nunca con MD5/SHA-1
