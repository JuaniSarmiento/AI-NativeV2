# Modelo de Seguridad — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto, revisores académicos (tesis doctoral UTN FRM)
**Clasificación**: Documentación interna — seguridad

---

## Índice

1. [Visión general del modelo de seguridad](#1-visión-general)
2. [Flujo de autenticación completo](#2-flujo-de-autenticación)
3. [Estructura del JWT](#3-estructura-del-jwt)
4. [Rotación de Refresh Tokens](#4-rotación-de-refresh-tokens)
5. [Hashing de contraseñas](#5-hashing-de-contraseñas)
6. [RBAC — Control de Acceso Basado en Roles](#6-rbac)
7. [Autenticación WebSocket](#7-autenticación-websocket)
8. [Rate Limiting](#8-rate-limiting)
9. [Configuración CORS](#9-configuración-cors)
10. [Security Headers](#10-security-headers)
11. [Token Blacklist en logout](#11-token-blacklist)
12. [Patrones de código de referencia](#12-patrones-de-código)

---

## 1. Visión general

La plataforma AI-Native maneja tres actores con distintos niveles de privilegio: **alumno**, **docente** y **admin**. El modelo de seguridad aplica defensa en profundidad con las siguientes capas:

```
[Cliente] → [CORS] → [Rate Limiter] → [Auth Middleware] → [RBAC] → [Handler]
                                                                        ↓
                                                                   [Sandbox / LLM / DB]
```

Principios aplicados:
- **Least privilege**: cada rol solo accede a sus recursos.
- **Zero trust en WebSocket**: la sesión WS verifica el JWT en el handshake antes de hacer upgrade.
- **Inmutabilidad del CTR**: hash chain SHA-256 impide retroalimentación maliciosa del registro de interacciones.
- **Separación de secretos**: credenciales nunca en código fuente; env vars en dev, Docker secrets en prod.

---

## 2. Flujo de Autenticación

### 2.1 Registro

```
POST /api/v1/auth/register
Body: { email, password, full_name }

1. Validar formato email (pydantic EmailStr)
2. Verificar email no registrado (SELECT en DB)
3. Hashear password con bcrypt (cost factor 12)
4. Persistir usuario en operational.users con role="alumno" (asignado server-side)
5. Retornar 201 Created (sin tokens — requiere login explícito)
```

**Notas de diseño**:
- El campo `role` **NO** está en el request body. El rol por defecto es `alumno`. Solo un admin puede asignar roles `docente` o `admin` via endpoint dedicado (`POST /admin/users/{id}/role`).
- No se envían tokens en el registro para evitar que bots creen cuentas y usen recursos de LLM inmediatamente.

### 2.2 Login

```
POST /api/v1/auth/login
Body: { email, password }

1. Buscar usuario por email
2. Verificar bcrypt hash (bcrypt.checkpw)
3. Si inválido → 401 Unauthorized (mismo mensaje que "usuario no existe" — anti-enumeration)
4. Generar access token (JWT, 15 min TTL)
5. Generar refresh token (JWT, 7 días TTL, jti único)
6. Guardar refresh token en Redis: SET auth:refresh:{jti} {user_id} EX 604800
7. Retornar { access_token, token_type: "bearer" } en el body
   + Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh
   (El access token va en el body para almacenarlo en Zustand; el refresh token va en cookie httpOnly para que JavaScript no pueda leerlo)
```

### 2.3 Uso del Access Token

```
Authorization: Bearer <access_token>

1. Middleware extrae Bearer token del header
2. Verifica firma JWT con SECRET_KEY
3. Verifica exp (expirado → 401)
4. Verifica jti no está en blacklist Redis (auth:blacklist:{jti})
5. Inyecta current_user en request state
6. Handler ejecuta lógica de negocio
```

### 2.4 Refresh de Token

```
POST /api/v1/auth/refresh
Cookie: refresh_token=<token>  (httpOnly cookie, enviada automáticamente por el browser)

1. Leer refresh token de la cookie httpOnly (NO del body)
2. Verificar firma JWT del refresh token (algorithms=["HS256"])
3. Verificar exp (expirado → 401, debe re-loguearse)
4. Buscar jti en Redis: GET auth:refresh:{jti}
5. Si no existe → 401 + invalidar TODAS las sesiones del usuario  ← detección de robo
6. DEL auth:refresh:{jti}                    ← invalida token viejo
7. Generar nuevo access token (15 min)
8. Generar nuevo refresh token (7 días, nuevo jti)
9. SET auth:refresh:{new_jti} {user_id} EX 604800
10. Retornar { access_token } en el body
    + Set-Cookie: refresh_token=<nuevo_token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh
```

**Propiedad de seguridad**: si un refresh token es robado y el atacante lo usa antes que el usuario legítimo, el próximo intento del usuario legítimo detectará que el jti ya no existe en Redis. Esto indica compromiso de sesión → se invalidan TODAS las sesiones activas del usuario (DEL de todos los `auth:refresh:*` para ese `user_id`), forzando re-autenticación completa.

**Token storage**:
- Access token: almacenado en Zustand (memoria), se pierde al recargar la página.
- Refresh token: en cookie httpOnly — el browser lo envía automáticamente al recargar, permitiendo obtener un nuevo access token sin re-login.

### 2.5 Logout

```
POST /api/v1/auth/logout
Headers: Authorization: Bearer <access_token>
Cookie: refresh_token=<token>  (httpOnly cookie, enviada automáticamente)

1. Extraer jti del access token
2. Calcular TTL restante del access token
3. SETEX auth:blacklist:{jti} {ttl_restante} "1"
4. Leer refresh token de la cookie → DEL auth:refresh:{refresh_jti}
5. Set-Cookie: refresh_token=; HttpOnly; Secure; Max-Age=0  ← limpia la cookie
6. Retornar 204 No Content
```

---

## 3. Estructura del JWT

### Access Token

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id_uuid",
    "role": "alumno",
    "email": "juan@example.com",
    "jti": "uuid4-único-por-token",
    "iat": 1712000000,
    "exp": 1712000900,
    "type": "access"
  }
}
```

**Campos del payload**:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sub` | UUID string | ID del usuario (FK a operational.users) |
| `role` | enum | `alumno` \| `docente` \| `admin` |
| `email` | string | Email para logging/audit (evita join a DB) |
| `jti` | UUID string | JWT ID único — permite blacklist individual |
| `iat` | Unix timestamp | Issued at — cuándo fue emitido |
| `exp` | Unix timestamp | Expiry — 15 minutos desde iat |
| `type` | string | `"access"` — distingue del refresh token |

### Refresh Token

Mismo formato pero con:
- `"type": "refresh"`
- `exp` = iat + 604800 (7 días)
- No incluye `role` ni `email` (mínimo necesario para rotación)

### Algoritmo de firma

**HS256** (HMAC-SHA256) con `SECRET_KEY` de 256 bits mínimo. La clave se genera con `openssl rand -hex 32` y se almacena en variables de entorno.

**Consideración futura**: migrar a RS256 (asimétrico) si se escala a microservicios, permitiendo que servicios internos solo necesiten la clave pública para verificar.

---

## 4. Rotación de Refresh Tokens

La rotación previene el reuso de tokens robados (refresh token rotation pattern):

```
Usuario                  Backend                     Redis
   │                        │                           │
   │── POST /auth/refresh ──>│                           │
   │   Cookie: refresh_token=T1 │                        │
   │                        │── GET auth:refresh:{jti1} ─>│
   │                        │<── user_id ────────────────│
   │                        │── DEL auth:refresh:{jti1} ─>│  ← invalida T1
   │                        │── SET auth:refresh:{jti2} ─>│  ← registra T2
   │<── { access_token: A2, │                           │
   │     refresh_token: T2 }│                           │
```

**Redis key schema para refresh tokens**:
```
auth:refresh:{jti}    →  {user_id}    TTL: 604800s (7 días)
```

**Redis key schema para blacklist**:
```
auth:blacklist:{jti}  →  "1"          TTL: tiempo restante del access token
```

---

## 5. Hashing de Contraseñas

**Algoritmo**: bcrypt con salt automático.
**Cost factor**: 12 (balance entre seguridad y performance — ~300ms en hardware moderno).

```python
import bcrypt

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

**Por qué bcrypt y no argon2id**: bcrypt es ampliamente soportado, bien comprendido en contextos académicos, y suficiente para el volumen esperado (< 10k usuarios). Argon2id sería preferible en sistemas de alta escala pero introduce complejidad de dependencias innecesaria para el alcance de la tesis.

**Política de contraseñas** (validada en capa Pydantic, no en DB):
- Mínimo 8 caracteres
- Al menos una mayúscula, una minúscula, un dígito
- No puede ser igual al email del usuario
- No se almacena nunca en texto plano, ni en logs

---

## 6. RBAC — Control de Acceso Basado en Roles

### 6.1 Roles definidos

| Rol | Descripción |
|-----|-------------|
| `alumno` | Estudiante — accede al tutor, sus propias sesiones, sus métricas |
| `docente` | Profesor — accede a datos de alumnos de su curso, puede ver analytics |
| `admin` | Administrador — acceso total, gestión de usuarios, configuración del sistema |

### 6.2 Matriz de permisos

| Recurso / Acción | alumno | docente | admin |
|------------------|--------|---------|-------|
| `WS /ws/tutor/chat` | Propias (rate limited) | — | — |
| `GET /teacher/tutor/interactions` | — | Alumnos de su comisión (read-only) | Todos |
| `POST /courses/{id}/exercises` | — | Si es owner del curso | Todas |
| `GET /courses/{id}/exercises` | Si inscripto | Del curso | Todas |
| `POST /student/exercises/{id}/submit` | Propias | — | — |
| `GET /student/submissions/{id}` | Propias | Alumnos de su comisión (read-only) | Todas |
| `GET /teacher/students/{id}/profile` | Propio | Alumnos de su comisión | Todos |
| `GET /teacher/courses/{id}/dashboard` | — | Su curso | Todas |
| `GET /teacher/sessions/{id}/trace` | — | Alumnos de su comisión (read-only) | Todas |
| `POST /admin/users/{id}/role` | — | — | Si |
| `GET /admin/tutor/system-prompts` | — | — | Si |
| `GET /api/v1/health` | Si | Si | Si |

### 6.3 Implementación: Dependency en FastAPI

```python
# app/core/security/dependencies.py
from fastapi import Depends, HTTPException, status
from app.core.security.jwt import decode_token
from app.models.user import UserRole

class RequireRole:
    """Dependency que verifica que el usuario tenga al menos uno de los roles requeridos."""

    def __init__(self, *roles: UserRole):
        self.required_roles = set(roles)

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in self.required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {self.required_roles}. Rol actual: {current_user['role']}",
            )
        return current_user


# Factories de uso frecuente
require_admin = RequireRole(UserRole.ADMIN)
require_docente = RequireRole(UserRole.DOCENTE, UserRole.ADMIN)
require_any = RequireRole(UserRole.ALUMNO, UserRole.DOCENTE, UserRole.ADMIN)
```

### 6.4 Ejemplo de uso en router

```python
# app/api/v1/exercises.py
from fastapi import APIRouter, Depends
from app.core.security.dependencies import require_docente, require_any

router = APIRouter(prefix="/exercises", tags=["exercises"])

@router.post("/", dependencies=[Depends(require_docente)])
async def create_exercise(body: ExerciseCreate, db: AsyncSession = Depends(get_db)):
    """Solo docentes y admins pueden crear ejercicios."""
    ...

@router.get("/{exercise_id}", dependencies=[Depends(require_any)])
async def get_exercise(exercise_id: UUID, ...):
    """Cualquier usuario autenticado puede ver ejercicios de su curso."""
    ...
```

### 6.5 Verificación de ownership (IDOR prevention)

Para recursos propios del alumno, no basta con el rol — hay que verificar que el recurso pertenece al usuario:

```python
async def get_own_session(
    session_id: UUID,
    current_user: dict = Depends(require_any),
    db: AsyncSession = Depends(get_db),
) -> TutorSession:
    session = await session_repo.get_by_id(session_id, db)
    if session is None:
        raise HTTPException(404, "Sesión no encontrada")

    # IDOR check: alumno solo puede ver sus propias sesiones
    if current_user["role"] == "alumno" and session.user_id != current_user["sub"]:
        raise HTTPException(403, "Sin acceso a esta sesión")

    return session
```

---

## 7. Autenticación WebSocket

Las conexiones WebSocket no pueden enviar headers HTTP customizados después del handshake inicial. La solución canónica es pasar el JWT como query parameter en la URL de conexión (`?token=`). La autenticación ocurre ANTES del upgrade, en el handshake. No se usa autenticación por "primer mensaje" — si el token es inválido, la conexión se rechaza antes de hacer `websocket.accept()`.

### 7.1 Flujo de handshake

```
Cliente                              Backend
   │                                    │
   │── WS ws://api/ws?token=<jwt> ──────>│
   │                                    │── Extraer token de query params
   │                                    │── Verificar firma JWT
   │                                    │── Verificar exp
   │                                    │── Verificar blacklist en Redis
   │                                    │── Si inválido: close(4001, "Unauthorized")
   │                                    │── Si válido: upgrade a WebSocket
   │<──── 101 Switching Protocols ──────│
   │                                    │── Registrar connection_id → user_id
   │  ←──── Sesión WS activa ──────────>│
```

### 7.2 Implementación del endpoint WS

```python
# app/api/v1/ws/tutor_ws.py
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.core.security.jwt import decode_token, is_blacklisted
from app.core.ws.connection_manager import manager

@router.websocket("/ws/tutor")
async def tutor_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    # Autenticar ANTES de hacer el accept()
    # decode_token usa algorithms=["HS256"] explícitamente (ver jwt.py, sección 12.1)
    try:
        payload = decode_token(token)  # raises si inválido/expirado; enforce algorithms=["HS256"]
        if await is_blacklisted(payload["jti"]):
            await websocket.close(code=4001, reason="Token invalidado")
            return
    except (JWTError, ExpiredSignatureError):
        await websocket.close(code=4001, reason="Token inválido o expirado")
        return

    await websocket.accept()
    connection_id = await manager.connect(websocket, user_id=payload["sub"])

    try:
        while True:
            data = await websocket.receive_json()
            await handle_tutor_message(data, payload, connection_id, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
```

**Consideración de seguridad**: el token en query string aparece en logs del servidor. Mitigación: usar tokens de corta vida (15 min del access token) y asegurarse que los logs de Nginx/proxy no logueen query strings en producción.

---

## 8. Rate Limiting

### 8.1 Estrategia: Sliding Window con Redis

Se implementa un sliding window counter en Redis. Más justo que fixed window (evita burst al borde del minuto) y más eficiente que sliding window log.

```python
# app/core/security/rate_limiter.py
import time
import redis.asyncio as redis
from fastapi import Request, HTTPException

class SlidingWindowRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        window_start = now - window_seconds

        pipe = self.redis.pipeline()
        # Remover entradas fuera de la ventana
        pipe.zremrangebyscore(key, 0, window_start)
        # Agregar request actual
        pipe.zadd(key, {str(now): now})
        # Contar requests en la ventana
        pipe.zcard(key)
        # Establecer TTL para limpieza automática
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        count = results[2]
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "retry_after": window_seconds,
                },
                headers={"Retry-After": str(window_seconds)},
            )
```

### 8.2 Configuraciones de límites

| Endpoint | Clave Redis | Límite | Ventana | Justificación |
|----------|-------------|--------|---------|---------------|
| `WS /ws/tutor/chat` (por msg) | `rl:tutor:{user_id}:{exercise_id}` | 30 | 3600s (1h) | Controla costo de API Anthropic, límite por ejercicio |
| `POST /api/v1/*` | `rl:api:{ip}` | 100 | 60s | Previene flooding general |
| `POST /auth/login` | `rl:login:{ip}` | 10 | 300s (5min) | Previene brute force |
| `POST /auth/register` | `rl:register:{ip}` | 5 | 3600s | Previene creación masiva de cuentas |
| `POST /student/exercises/{id}/run` | `rl:sandbox:{user_id}` | 30 | 60s | Controla recursos del sandbox |

### 8.3 Dependency de FastAPI para rate limiting

```python
# app/core/security/dependencies.py
from app.core.security.rate_limiter import SlidingWindowRateLimiter

def rate_limit(limit: int, window_seconds: int, scope: str = "api"):
    """Factory para crear dependencies de rate limiting."""

    async def dependency(
        request: Request,
        current_user: dict | None = None,
    ):
        limiter = SlidingWindowRateLimiter(request.app.state.redis)

        if scope == "tutor" and current_user:
            exercise_id = request.path_params.get("exercise_id") or request.query_params.get("exercise_id", "default")
            key = f"rl:tutor:{current_user['sub']}:{exercise_id}"
        elif scope == "login":
            key = f"rl:login:{request.client.host}"
        else:
            key = f"rl:api:{request.client.host}"

        await limiter.check(key, limit, window_seconds)

    return Depends(dependency)


# Uso:
@router.post("/tutor/message", dependencies=[
    Depends(require_any),
    rate_limit(30, 3600, "tutor"),
])
async def send_tutor_message(...): ...
```

---

## 9. Configuración CORS

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS_DEV = ["http://localhost:5173"]
ALLOWED_ORIGINS_PROD = [settings.FRONTEND_URL]  # desde env var

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_DEV if settings.DEBUG else ALLOWED_ORIGINS_PROD,
    allow_credentials=True,          # necesario para cookies httpOnly (refresh token)
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    max_age=600,                     # preflight cache 10 minutos
)
```

**Notas**:
- En desarrollo: solo `http://localhost:5173` (puerto del Vite dev server).
- En producción: dominio HTTPS del frontend, configurado via `FRONTEND_URL` env var.
- `allow_credentials=True` es necesario para que el browser envíe la cookie httpOnly del refresh token.
- El wildcard `"*"` en `allow_origins` está **explícitamente prohibido** — rompe `allow_credentials`.

---

## 10. Security Headers

Configurados via middleware personalizado en FastAPI:

```python
# app/middleware/security_headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if not settings.DEBUG:
            # Solo en HTTPS (producción)
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content-Security-Policy — ajustar según necesidades del frontend
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; "   # Monaco Editor requiere wasm-unsafe-eval para WASM workers. NO usar unsafe-inline.
            "style-src 'self' 'unsafe-inline'; "    # TailwindCSS inline styles
            "connect-src 'self' wss:; "             # Solo WSS (TLS) en producción. ws:// solo en dev via override local.
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none'"
        )
        # NOTA: En desarrollo local, se puede agregar ws://localhost:8000 en connect-src via middleware condicional.
        # En producción: NUNCA incluir ws:// ni 'unsafe-inline' en script-src.

        return response
```

**Tabla de headers y propósito**:

| Header | Valor | Protección |
|--------|-------|------------|
| `X-Content-Type-Options` | `nosniff` | Previene MIME sniffing — evita que browser interprete JS desde respuestas no-JS |
| `X-Frame-Options` | `DENY` | Previene clickjacking via iframes |
| `X-XSS-Protection` | `1; mode=block` | Activa filtro XSS del browser (legacy, complemento a CSP) |
| `HSTS` | `max-age=31536000; includeSubDomains` | Fuerza HTTPS por 1 año. Solo en producción |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limita qué URL se envía en el header Referer |
| `CSP` | `script-src 'self' 'wasm-unsafe-eval'`, `connect-src 'self' wss:` | Previene XSS declarando fuentes permitidas. NO `unsafe-inline` en `script-src`. |
| `Permissions-Policy` | (ver arriba) | Desactiva APIs del browser no usadas (cámara, etc.) |

---

## 11. Token Blacklist en Logout

El JWT es stateless por diseño, lo que implica que un token válido seguirá siéndolo hasta su expiración aunque el usuario haga logout. La blacklist en Redis resuelve esto:

```
Redis key: auth:blacklist:{jti}
Value: "1"
TTL: tiempo restante del token (exp - now)
```

**Verificación en cada request**:

```python
# app/core/security/jwt.py
import redis.asyncio as redis_async

async def is_blacklisted(jti: str, redis_client: redis_async.Redis) -> bool:
    result = await redis_client.get(f"auth:blacklist:{jti}")
    return result is not None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis_client: redis_async.Redis = Depends(get_redis),
) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Token inválido")

    if await is_blacklisted(payload["jti"], redis_client):
        raise HTTPException(401, "Sesión terminada")

    return payload
```

**Overhead aceptable**: cada request autenticada hace 1 GET en Redis (~0.5ms local). Comparado con una query a PostgreSQL por sesión (~5-20ms), el overhead es mínimo y el beneficio de seguridad es significativo.

---

## 12. Patrones de Código

### 12.1 Middleware de autenticación completo

```python
# app/core/security/jwt.py
from datetime import datetime, timedelta, timezone
import uuid
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def create_access_token(user_id: str, role: str, email: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Retorna (token_encoded, jti) para almacenar en Redis."""
    now = datetime.now(tz=timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256"), jti

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
```

### 12.2 Decorator de permisos avanzado

```python
# app/core/security/permissions.py
from functools import wraps
from typing import Callable
from fastapi import HTTPException

def require_ownership_or_role(*admin_roles: str):
    """
    Verifica que el usuario sea el dueño del recurso O tenga un rol admin.
    Uso: decorar el service method, no el handler.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: dict, resource_user_id: str, **kwargs):
            is_owner = current_user["sub"] == resource_user_id
            is_privileged = current_user["role"] in admin_roles

            if not (is_owner or is_privileged):
                raise HTTPException(
                    status_code=403,
                    detail="No tiene permiso para acceder a este recurso"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


# Uso en servicio:
@require_ownership_or_role("docente", "admin")
async def get_student_sessions(
    student_id: str,
    current_user: dict,
    db: AsyncSession,
) -> list[TutorSession]: ...
```

---

**Referencias internas**:
- `knowledge-base/03-seguridad/02_superficie_de_ataque.md` — análisis de vectores de ataque
- `knowledge-base/02-arquitectura/07_adrs.md` — decisiones de diseño de seguridad
- `scaffold-decisions.yaml` — fuente de verdad de configuración de seguridad
