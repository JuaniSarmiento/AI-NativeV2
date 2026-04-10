# Referencia de Skills — Claude Code

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Este documento es una referencia rápida de todos los skills de Claude Code configurados para este proyecto. Cada skill encapsula patrones y convenciones específicas del stack para que los agentes de IA generen código consistente con el proyecto.

---

## Indice de Skills

1. [fastapi-domain-service](#1-fastapi-domain-service)
2. [sqlalchemy-patterns](#2-sqlalchemy-patterns)
3. [zustand-store-pattern](#3-zustand-store-pattern)
4. [tailwind-theme-system](#4-tailwind-theme-system)
5. [redis-best-practices](#5-redis-best-practices)
6. [websocket-patterns](#6-websocket-patterns)
7. [api-security](#7-api-security)

---

## 1. fastapi-domain-service

**Propósito**: Generar routers y servicios de FastAPI siguiendo la arquitectura en capas del proyecto (thin routers, domain services, permission context).

### Cuándo usar este skill

- Al crear un nuevo router FastAPI
- Al implementar la lógica de negocio de un servicio de dominio
- Al añadir nuevos endpoints a módulos existentes
- Al implementar middleware o dependencias de FastAPI

### Patrones que encapsula

**Thin Router**: Los routers solo validan el request y delegan al service.

```python
# PATRÓN: Thin router
@router.post("/", response_model=SuccessResponse[ExerciseResponse], status_code=201)
async def create_exercise(
    request: CreateExerciseRequest,
    current_user: User = Depends(get_current_user),
    service: ExerciseService = Depends(get_exercise_service),
) -> SuccessResponse[ExerciseResponse]:
    result = await service.create_exercise(request, current_user)
    return SuccessResponse(data=ExerciseResponse.model_validate(result))
```

**Domain Service**: Toda la lógica de negocio, orquesta repositorios.

```python
# PATRÓN: Domain service
class ExerciseService:
    def __init__(self, repository: ExerciseRepository):
        self._repo = repository
    
    async def create_exercise(
        self,
        request: CreateExerciseRequest,
        created_by: User,
    ) -> Exercise:
        if not created_by.can_create_exercises():
            raise InsufficientPermissionsError("Only professors can create exercises")
        
        exercise = Exercise(
            title=request.title,
            description=request.description,
            difficulty=request.difficulty,
            created_by_id=created_by.id,
        )
        return await self._repo.create(exercise)
```

**Permission Context**: Los permisos se verifican en el service, no en el router.

```python
# PATRÓN: Permission en el service
async def delete_exercise(self, exercise_id: UUID, current_user: User) -> None:
    exercise = await self._repo.find_by_id(exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError(exercise_id)
    
    if not current_user.is_admin() and exercise.created_by_id != current_user.id:
        raise InsufficientPermissionsError("Can only delete your own exercises")
    
    await self._repo.soft_delete(exercise_id)
```

### Convenciones específicas

- Un router por feature: `exercise_router.py`, `tutor_router.py`
- Un service por feature: `exercise_service.py`, `tutor_service.py`
- Inyección via `Depends()` en el router
- Respuesta siempre envuelta en `SuccessResponse[T]`
- Errores de dominio como excepciones Python, convertidas a HTTP en el exception handler global

---

## 2. sqlalchemy-patterns

**Propósito**: Generar código SQLAlchemy 2.0 async correcto, con carga de relaciones explícita, multi-schema, y prevención de N+1.

### Cuándo usar este skill

- Al crear nuevos modelos SQLAlchemy
- Al escribir queries en repositorios
- Al crear migraciones Alembic
- Al configurar relaciones entre modelos

### Patrones que encapsula

**Async Session**: Siempre usar `AsyncSession`, nunca `Session` síncrona.

```python
# PATRÓN: Async repository
class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    
    async def find_by_id(self, exercise_id: UUID) -> Exercise | None:
        result = await self._session.execute(
            select(Exercise)
            .options(selectinload(Exercise.test_cases))  # cargar relaciones explícitamente
            .where(Exercise.id == exercise_id)
            .where(Exercise.is_active.is_(True))
        )
        return result.scalar_one_or_none()
```

**Prevención de N+1**: Siempre `selectinload` para colecciones, `joinedload` para objetos únicos.

```python
# PATRÓN: Evitar N+1 en listados
async def find_all_with_submissions(self) -> list[Exercise]:
    result = await self._session.execute(
        select(Exercise)
        .options(
            selectinload(Exercise.test_cases),        # colección → selectinload
            joinedload(Exercise.created_by),          # objeto único → joinedload
        )
        .where(Exercise.is_active.is_(True))
        .order_by(Exercise.created_at.desc())
    )
    return list(result.scalars().unique())
```

**Multi-schema**: Siempre especificar `schema=` en `__table_args__`.

```python
# PATRÓN: Modelo multi-schema
class CognitiveTraceRecord(Base):
    __tablename__ = "cognitive_trace_records"
    __table_args__ = {"schema": "cognitive"}  # OBLIGATORIO
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
```

**Boolean comparisons**: Usar `.is_()` y `.is_not()`, nunca `== True`.

```python
# PATRÓN: Booleanos correctos
query = select(User).where(User.is_active.is_(True))
query = select(Exercise).where(Exercise.deleted_at.is_(None))
```

---

## 3. zustand-store-pattern

**Propósito**: Generar stores de Zustand 5 con selectores correctos, `useShallow` para evitar re-renders, `persist` y `devtools` configurados.

### Cuándo usar este skill

- Al crear un nuevo store de Zustand
- Al agregar estado a un store existente
- Al consumir un store desde un componente React
- Al configurar persistencia de estado

### Patrones que encapsula

**Store con devtools**: Siempre envolver con `devtools` en desarrollo.

```typescript
// PATRÓN: Store base
export const useExerciseStore = create<ExerciseStore>()(
  devtools(
    (set, get) => ({
      exercises: [],
      // ...
    }),
    { name: 'ExerciseStore' }
  )
)
```

**Selectores para evitar re-renders**: Nunca destructurar el store directamente.

```typescript
// PATRÓN: Selector de valor único
const userName = useAuthStore((state) => state.user?.name)

// PATRÓN: Múltiples valores con useShallow
const { isAuthenticated, user } = useAuthStore(
  useShallow((state) => ({
    isAuthenticated: state.isAuthenticated,
    user: state.user,
  }))
)
```

**Fallback estable para arrays**: Usar constante fuera del componente.

```typescript
// PATRÓN: Fallback estable
const EMPTY_ARRAY: Exercise[] = []  // fuera del componente
const exercises = useExerciseStore((state) => state.exercises ?? EMPTY_ARRAY)
```

**Persist para auth**: El store de auth persiste en localStorage.

```typescript
// PATRÓN: Store con persist
export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        accessToken: null,
        // ...
      }),
      {
        name: 'auth-store',
        partialize: (state) => ({ user: state.user, accessToken: state.accessToken }),
      }
    ),
    { name: 'AuthStore' }
  )
)
```

---

## 4. tailwind-theme-system

**Propósito**: Generar componentes con el design system del proyecto: tokens de color, dark mode, tipografía, spacing, y patrones responsivos.

### Cuándo usar este skill

- Al crear nuevos componentes UI
- Al aplicar dark mode a componentes existentes
- Al implementar layouts responsivos
- Al definir variantes de componentes

### Patrones que encapsula

**Tokens de color**: Usar variables CSS del design system, no colores hardcodeados.

```tsx
// PATRÓN: Usar tokens del design system
// Correcto: usa variables del theme
<div className="bg-surface-primary text-content-primary border border-border-subtle">

// Incorrecto: hardcodeado
<div className="bg-gray-100 text-gray-900 border border-gray-200">
```

**Dark mode**: Usar el modifier `dark:` para todas las variantes.

```tsx
// PATRÓN: Dark mode
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
```

**Responsivo**: Mobile-first con breakpoints `sm:`, `md:`, `lg:`.

```tsx
// PATRÓN: Responsivo
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
```

**Componentes con variantes**: Usar `cva` (class-variance-authority) para variantes de componentes.

```typescript
// PATRÓN: Variantes con cva
import { cva } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors',
  {
    variants: {
      variant: {
        primary: 'bg-primary-600 text-white hover:bg-primary-700',
        secondary: 'bg-secondary-100 text-secondary-900 hover:bg-secondary-200',
        ghost: 'hover:bg-accent-100 hover:text-accent-900',
      },
      size: {
        sm: 'h-8 px-3',
        md: 'h-10 px-4',
        lg: 'h-12 px-6',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)
```

---

## 5. redis-best-practices

**Propósito**: Generar código de Redis con naming conventions correctas, TTLs apropiados, patrones de Pub/Sub y Streams, y sin usar el comando KEYS.

### Cuándo usar este skill

- Al implementar caché con Redis
- Al usar Redis para sesiones o tokens
- Al implementar Pub/Sub para eventos en tiempo real
- Al usar Redis Streams para procesamiento de eventos

### Patrones que encapsula

**Key naming**: Estructura `{app}:{entity}:{id}:{field}`.

```python
# PATRÓN: Naming de keys
AUTH_TOKEN_KEY = "ainative:auth:token:{token_jti}"
USER_SESSION_KEY = "ainative:session:user:{user_id}"
EXERCISE_CACHE_KEY = "ainative:cache:exercise:{exercise_id}"
TUTOR_RATE_LIMIT_KEY = "ainative:rate_limit:tutor:user:{user_id}"
```

**TTL obligatorio**: Todo lo que se escribe en Redis debe tener TTL.

```python
# PATRÓN: Siempre con TTL
await redis.setex(
    AUTH_TOKEN_KEY.format(token_jti=jti),
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    "blacklisted"
)
# NUNCA: await redis.set(key, value)  # sin TTL → memoria leak
```

**NUNCA usar KEYS**: En producción, `KEYS *` bloquea Redis. Usar `SCAN`.

```python
# PATRÓN: SCAN en lugar de KEYS
async def get_all_user_sessions(user_id: UUID) -> list[str]:
    pattern = f"ainative:session:user:{user_id}:*"
    keys = []
    async for key in redis.scan_iter(match=pattern, count=100):
        keys.append(key)
    return keys

# NUNCA: keys = await redis.keys("ainative:session:*")  # bloquea Redis
```

**Pub/Sub para eventos del tutor**:

```python
# PATRÓN: Publicar evento
await redis.publish(
    f"ainative:tutor:session:{session_id}",
    json.dumps({"type": "message", "content": text_chunk})
)
```

---

## 6. websocket-patterns

**Propósito**: Generar código de WebSocket con lifecycle completo: autenticación en la conexión, heartbeat, reconexión del cliente, y manejo de desconexión limpia.

### Cuándo usar este skill

- Al implementar endpoints WebSocket en FastAPI
- Al implementar el cliente WebSocket en React
- Al manejar reconexiones automáticas
- Al implementar broadcasting de eventos

### Patrones que encapsula

**Autenticación manual en WS**: No usar `Depends()` para auth en WebSocket.

```python
# PATRÓN: Auth manual en WebSocket
@router.websocket("/ws/tutor/{session_id}")
async def tutor_websocket(websocket: WebSocket, session_id: UUID, token: str = Query(...)):
    await websocket.accept()
    try:
        user = await authenticate_ws_token(token)
    except AuthenticationError:
        await websocket.close(code=4001)
        return
    
    try:
        await handle_tutor_session(websocket, user, session_id)
    except WebSocketDisconnect:
        pass  # normal disconnect
    finally:
        await cleanup_session(session_id)
```

**Heartbeat server-side**: Enviar ping cada 25 segundos.

```python
# PATRÓN: Heartbeat
async def handle_tutor_session(websocket: WebSocket, user: User, session_id: UUID):
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_json(), timeout=25.0)
            await process_message(websocket, user, session_id, message)
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "ping"})
```

**Reconexión en cliente**: Backoff exponencial.

```typescript
// PATRÓN: Reconexión automática
class TutorWebSocket {
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return
    
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000)
    setTimeout(() => {
      this.reconnectAttempts++
      this.connect()  // re-autentica en cada reconexión
    }, delay)
  }
}
```

---

## 7. api-security

**Propósito**: Generar código de autenticación y autorización: JWT guards, refresh token rotation, RBAC, CORS, y rate limiting.

### Cuándo usar este skill

- Al proteger endpoints con autenticación
- Al implementar control de acceso basado en roles
- Al configurar rate limiting
- Al revisar configuraciones de CORS y headers de seguridad

### Patrones que encapsula

**JWT Guard como Dependency**:

```python
# PATRÓN: Dependencia de autenticación
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_jwt(token)
        user = await get_user_by_id(UUID(payload["sub"]), session)
        if user is None or not user.is_active:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# En el router:
current_user: User = Depends(get_current_user)
```

**RBAC con decoradores**:

```python
# PATRÓN: Require role
def require_role(*roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return dependency

# En el router:
current_user: User = Depends(require_role(UserRole.PROFESSOR, UserRole.ADMIN))
```

**Rate limiting con Redis**:

```python
# PATRÓN: Rate limiting sliding window
async def check_rate_limit(user_id: UUID, action: str, limit: int, window: int):
    key = f"ainative:rate_limit:{action}:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    if count > limit:
        raise RateLimitExceededError(f"Rate limit exceeded for {action}")
```

**Refresh token rotation**: El refresh token se invalida al usarse y se emite uno nuevo.

```python
# PATRÓN: Rotation
async def refresh_tokens(refresh_token: str) -> tuple[str, str]:
    payload = decode_jwt(refresh_token, expected_type="refresh")
    
    # Verificar que no fue usado/invalidado
    if await is_token_blacklisted(payload["jti"]):
        raise TokenRevokedError()
    
    # Invalidar el token actual
    await blacklist_token(payload["jti"], expires_in=payload["exp"] - time.time())
    
    # Emitir nuevos tokens
    user = await get_user_by_id(UUID(payload["sub"]))
    return create_access_token(user), create_refresh_token(user)
```
