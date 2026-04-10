# Trampas Conocidas — Gotchas del Stack

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Este documento reúne errores no obvios, comportamientos contraintuitivos, y problemas ya resueltos en este stack y proyecto específico. Leerlo antes de empezar a codear puede ahorrarte horas de debugging.

---

## Indice

1. [SQLAlchemy Async](#1-sqlalchemy-async)
2. [Alembic Multi-Schema](#2-alembic-multi-schema)
3. [FastAPI](#3-fastapi)
4. [Zustand 5](#4-zustand-5)
5. [React 19](#5-react-19)
6. [WebSockets](#6-websockets)
7. [Hash Chain — CTR](#7-hash-chain--ctr)
8. [Sandbox de Python](#8-sandbox-de-python)
9. [Pydantic v2](#9-pydantic-v2)
10. [PostgreSQL Específico](#10-postgresql-específico)
11. [Anthropic API](#11-anthropic-api)
12. [Testing Async](#12-testing-async)

---

## 1. SQLAlchemy Async

### Lazy loading falla silenciosamente (o lanza excepción)

**Problema**: En SQLAlchemy asíncrono, acceder a una relación sin haberla cargado explícitamente lanza `MissingGreenlet: greenlet_spawn has not been called` o retorna un objeto no-cargado que falla al serializar.

```python
# INCORRECTO: lazy loading no funciona en async
async def get_user_with_exercises(user_id: UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    return user.exercises  # FALLA: lazy load no disponible en contexto async
```

**Solución**: Siempre cargar relaciones explícitamente con `selectinload` o `joinedload`:

```python
# CORRECTO: selectinload (genera una segunda query SELECT IN)
from sqlalchemy.orm import selectinload

async def get_user_with_exercises(user_id: UUID) -> User:
    result = await session.execute(
        select(User)
        .options(selectinload(User.exercises))
        .where(User.id == user_id)
    )
    return result.scalar_one()

# CORRECTO: joinedload (genera un JOIN, mejor para relaciones many-to-one)
from sqlalchemy.orm import joinedload

async def get_ctr_with_user(ctr_id: UUID) -> CognitiveTraceRecord:
    result = await session.execute(
        select(CognitiveTraceRecord)
        .options(joinedload(CognitiveTraceRecord.user))
        .where(CognitiveTraceRecord.id == ctr_id)
    )
    return result.scalar_one()
```

**Regla de dedo**: `selectinload` para colecciones (one-to-many, many-to-many), `joinedload` para objetos únicos (many-to-one, one-to-one).

### `== True` vs `.is_(True)` en filtros booleanos

**Problema**: SQLAlchemy emite un warning (y en versiones futuras un error) cuando se usa `==` para comparar con booleanos en columnas nullable.

```python
# INCORRECTO: genera warning
query = select(User).where(User.is_active == True)
query = select(Exercise).where(Exercise.deleted_at == None)
```

**Solución**: Usar los métodos `.is_()` y `.is_not()`:

```python
# CORRECTO
query = select(User).where(User.is_active.is_(True))
query = select(Exercise).where(Exercise.deleted_at.is_(None))
query = select(CognitiveTraceRecord).where(CognitiveTraceRecord.is_active.is_not(False))
```

### Session scope incorrecto en tests

**Problema**: Compartir una `AsyncSession` entre múltiples tests causa que el estado de la base de datos se filtre entre tests.

```python
# INCORRECTO: session compartida entre todos los tests del módulo
@pytest.fixture(scope="module")
async def session():
    async with AsyncSession(engine) as s:
        yield s
```

**Solución**: La session debe tener scope `function` (default) y usar rollback al finalizar:

```python
# CORRECTO: session con rollback por test
@pytest.fixture
async def session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as s:
        async with s.begin():
            yield s
            await s.rollback()  # limpia el estado después de cada test
```

### `expire_on_commit=False` para respuestas post-commit

**Problema**: Después de un `session.commit()`, SQLAlchemy expira todos los atributos del objeto. Si intentás acceder a ellos fuera del contexto de la sesión (p.ej. al serializar el Pydantic schema), obtenés `DetachedInstanceError`.

```python
# INCORRECTO
async def create_user(data: CreateUserRequest, session: AsyncSession) -> UserResponse:
    user = User(**data.model_dump())
    session.add(user)
    await session.commit()
    return UserResponse.model_validate(user)  # DetachedInstanceError: atributos expirados
```

**Soluciones**:

```python
# Solución 1: refresh después del commit
await session.commit()
await session.refresh(user)
return UserResponse.model_validate(user)

# Solución 2: configurar la session con expire_on_commit=False
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,  # los atributos no se expiran al commitear
    class_=AsyncSession,
)
```

El proyecto usa `expire_on_commit=False` en la factory de sesiones de producción.

---

## 2. Alembic Multi-Schema

### Las migraciones deben especificar el schema

**Problema**: Alembic por defecto trabaja en el schema `public`. Si las tablas están en schemas específicos (`operational`, `cognitive`, etc.), las migraciones autogeneradas pueden omitir el schema o crear las tablas en `public`.

**Solución**: Especificar `schema=` en todos los objetos de Alembic:

```python
# INCORRECTO
op.create_table(
    'users',
    sa.Column('id', postgresql.UUID, primary_key=True),
)

# CORRECTO
op.create_table(
    'users',
    sa.Column('id', postgresql.UUID, primary_key=True),
    schema='operational',  # siempre especificar el schema
)

op.create_index('ix_users_email', 'users', ['email'], schema='operational')
op.add_column('users', sa.Column('last_login', sa.DateTime), schema='operational')
```

### El `env.py` de Alembic debe incluir todos los schemas en `search_path`

En `backend/alembic/env.py`, la configuración de conexión debe incluir todos los schemas:

```python
def run_migrations_online():
    connectable = engine_from_config(...)
    
    with connectable.connect() as connection:
        connection.execute(text(
            "SET search_path TO operational, cognitive, governance, analytics, public"
        ))
        context.configure(
            connection=connection,
            target_metadata=metadata,
            include_schemas=True,       # OBLIGATORIO para multi-schema
            version_table_schema='operational',  # tabla alembic_version en schema operational
        )
```

### El autogenerate no detecta cambios entre schemas

**Problema**: Cuando los modelos SQLAlchemy y las tablas existentes están en schemas diferentes, `--autogenerate` puede generar migraciones que intentan recrear tablas ya existentes.

**Solución**: Incluir un filtro de inclusión de schemas en `env.py`:

```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "schema" and name not in [
        "operational", "cognitive", "governance", "analytics"
    ]:
        return False
    return True

context.configure(
    ...,
    include_object=include_object,
)
```

---

## 3. FastAPI

### `Depends()` en WebSocket routes funciona diferente

**Problema**: En rutas HTTP normales, `Depends()` inyecta dependencias normalmente. En rutas WebSocket, las excepciones de HTTPException dentro de un Depends no se manejan automáticamente — la conexión puede quedar colgada.

```python
# INCORRECTO: HTTPException no se propaga correctamente en WebSocket
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user),  # puede fallar silenciosamente
):
    await websocket.accept()
    ...
```

**Solución**: Autenticar manualmente en WebSocket, capturar excepciones explícitamente:

```python
# CORRECTO
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    try:
        user = await authenticate_ws_token(token)
    except AuthenticationError:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    try:
        await handle_websocket_session(websocket, user)
    except WebSocketDisconnect:
        pass  # cliente desconectó normalmente
```

### Response model y None pueden ocultar errores de tipo

**Problema**: Si el `response_model` de un endpoint devuelve un campo como opcional cuando debería ser requerido, FastAPI filtra los campos `None` sin advertir.

Siempre usar `response_model_exclude_none=True` con intención, no por defecto.

### Orden de importación de routers importa

Si dos routers tienen paths que podrían conflictuar (p.ej. `/exercises/{id}` y `/exercises/me`), el orden de inclusión en `app/main.py` determina cuál matchea primero. Siempre poner rutas más específicas antes:

```python
# CORRECTO: más específico primero
app.include_router(exercises_router)  # incluye /exercises/me antes de /exercises/{id}

# El router debe definir /me antes de /{id}:
# @router.get("/me")  <- va primero
# @router.get("/{exercise_id}")  <- va después
```

---

## 4. Zustand 5

### Destructuring del store causa re-renders innecesarios

**Problema**: Desestructurar múltiples valores del store hace que el componente re-renderice cada vez que *cualquier* valor del store cambia, no solo los que usa.

```typescript
// INCORRECTO: re-renderiza cuando cualquier cosa en authStore cambia
function UserBadge() {
  const { user, isAuthenticated, logout } = useAuthStore()
  return <span>{user?.name}</span>
}
```

**Solución**: Usar un selector para suscribirse solo a lo que se necesita:

```typescript
// CORRECTO: re-renderiza solo cuando user.name cambia
import { useShallow } from 'zustand/react/shallow'

function UserBadge() {
  const userName = useAuthStore((state) => state.user?.name)
  return <span>{userName}</span>
}

// Para múltiples valores: useShallow evita re-renders por referencia
function AuthButtons() {
  const { isAuthenticated, logout } = useAuthStore(
    useShallow((state) => ({
      isAuthenticated: state.isAuthenticated,
      logout: state.logout,
    }))
  )
  return isAuthenticated ? <button onClick={logout}>Salir</button> : null
}
```

### Array vacío como fallback crea nueva referencia en cada render

**Problema**: Usar `|| []` como fallback dentro de un selector crea un nuevo array en cada evaluación, lo que hace que `useShallow` siempre considere el valor como "cambiado".

```typescript
// INCORRECTO: nuevo array en cada render → re-render infinito posible
function ExerciseList() {
  const exercises = useExerciseStore((state) => state.exercises || [])
}
```

**Solución**: Usar una constante estable fuera del componente:

```typescript
// CORRECTO: misma referencia siempre
const EMPTY_EXERCISES: Exercise[] = []

function ExerciseList() {
  const exercises = useExerciseStore((state) => state.exercises ?? EMPTY_EXERCISES)
}
```

### Las acciones del store no deben ser async en la definición del tipo

**Problema**: Definir acciones async en el tipo del store de Zustand puede llevar a inconsistencias con el tipo real.

```typescript
// Convención del proyecto: acciones síncronas en el store,
// llamadas async se manejan en el componente o en un custom hook
interface ExerciseStore {
  exercises: Exercise[]
  setExercises: (exercises: Exercise[]) => void  // sync, no async
  isLoading: boolean
  setLoading: (loading: boolean) => void
}
```

El fetching de datos se maneja en hooks separados (`useExercises`, `useExerciseDetail`) que llaman a la API y luego actualizan el store con las acciones síncronas.

---

## 5. React 19

### `use()` hook solo funciona dentro de Suspense boundary

**Problema**: El nuevo hook `use()` de React 19 (que acepta Promises y Context) lanza si se usa fuera de un `<Suspense>` boundary.

```typescript
// INCORRECTO: falla sin Suspense
function ExerciseDetail({ id }: { id: string }) {
  const exercise = use(fetchExercise(id))  // throws si no hay Suspense arriba
  return <div>{exercise.title}</div>
}

// CORRECTO: envolver con Suspense
function ExercisePage({ id }: { id: string }) {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ExerciseDetail id={id} />
    </Suspense>
  )
}
```

En este proyecto, el uso de `use()` está limitado a casos muy específicos. La mayoría del fetching usa React Query o el patrón de custom hooks con Zustand.

### Server Components no aplican aquí

El proyecto es una SPA pura (Single Page Application) con Vite. No se usan React Server Components ni ninguna feature de SSR/SSG. Si ves documentación de Next.js sobre RSC, no aplica a este proyecto.

---

## 6. WebSockets

### Debe re-autenticarse en cada reconexión

**Problema**: Cuando un cliente WebSocket se desconecta y reconecta, la nueva conexión no tiene información del usuario anterior. No hay estado persistente en el servidor para identificar al cliente.

**Solución**: El cliente debe enviar el token de autenticación como query param o en el primer mensaje tras conectar:

```typescript
// En el cliente: siempre incluir el token en la URL
const ws = new WebSocket(`${WS_BASE_URL}/ws/session?token=${accessToken}`)

// O enviar como primer mensaje después de conectar
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', token: accessToken }))
}
```

El servidor verifica el token en el primer mensaje antes de procesar cualquier otro evento.

### No asumir que WebSocket está disponible

En entornos con proxies o firewalls institucionales (como redes universitarias), WebSocket puede estar bloqueado. El cliente debe tener fallback a long polling si WS falla.

### Heartbeat necesario para conexiones idle

Las conexiones WebSocket idle pueden ser cerradas por proxies/load balancers después de un timeout (usualmente 30-60 segundos). El servidor envía pings cada 25 segundos y el cliente debe responder con pong:

```typescript
// Cliente: responder a pings del servidor
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong' }))
    return
  }
  // ... manejar otros mensajes
}
```

---

## 7. Hash Chain — CTR

### La serialización JSONB debe ser determinista

**Problema**: El hash de cada CTR incluye su contenido serializado como JSON. Si el orden de las claves del JSON varía entre operaciones, el mismo objeto produce hashes diferentes.

```python
# INCORRECTO: dict normal no garantiza orden consistente (aunque Python 3.7+ mantiene inserción)
import json
content = {"b_field": 2, "a_field": 1}
hash_input = json.dumps(content)  # puede variar en algunas circunstancias
```

**Solución**: Siempre serializar con `sort_keys=True`:

```python
# CORRECTO: claves ordenadas garantizan determinismo
import json
import hashlib

def compute_ctr_hash(content: dict, previous_hash: str | None) -> str:
    payload = {
        "content": content,
        "previous_hash": previous_hash,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()
```

### Los CTR son inmutables — sin soft delete

Los CTR (Cognitive Trace Records) son el registro de evidencia del aprendizaje. A diferencia del resto del sistema que usa soft delete (`is_active=False`, `deleted_at`), los CTR **no tienen mecanismo de eliminación**. Una vez creados, son permanentes.

Si necesitás "invalidar" un CTR, se agrega un CTR de tipo `invalidation` que referencia al CTR inválido. El hash chain permanece intacto.

### El hash chain se verifica periódicamente

El sistema tiene un job programado que verifica la integridad del hash chain. Si se detecta una ruptura (hash no coincide con el expected), se genera una alerta en el schema `governance`. No modificar el hash chain fuera del código oficial de la plataforma.

---

## 8. Sandbox de Python

### Diferencias de comportamiento entre Windows y Linux

**Problema**: El sandbox que ejecuta el código Python de los estudiantes usa `subprocess` con restricciones. En Linux, se pueden usar restricciones de seccomp y namespaces. En Windows (incluyendo WSL2), algunas de estas restricciones no están disponibles.

**Impacto**: En desarrollo sobre WSL2, el sandbox puede ser menos restrictivo que en producción (Linux nativo). Siempre testear el sandbox en una VM Linux o en CI si hay cambios al mismo.

### Timeout del sandbox debe ser conservador

El timeout para ejecución de código de estudiantes está configurado en 5 segundos. Aumentarlo puede llevar a ataques de denegación de servicio (loops infinitos). Si un ejercicio legítimamente necesita más tiempo, hay que revisar el ejercicio, no el timeout.

### No confiar en el output del sandbox para lógica de negocio

El sandbox puede ser engañado por código malicioso que imprime el output esperado sin resolver el problema. La validación real usa casos de test, no el output de stdout.

---

## 9. Pydantic v2

### `model_config = ConfigDict(from_attributes=True)` para modelos ORM

**Problema**: Pydantic v2 cambió la forma de habilitar el parseo desde objetos ORM (SQLAlchemy models). El antiguo `class Config: orm_mode = True` ya no funciona.

```python
# INCORRECTO (Pydantic v1)
class UserResponse(BaseModel):
    id: UUID
    email: str
    
    class Config:
        orm_mode = True
```

```python
# CORRECTO (Pydantic v2)
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: str
```

Todos los schemas de respuesta que parsean desde SQLAlchemy models deben tener `from_attributes=True`. Los schemas de request no lo necesitan.

### `model_validate` vs `from_orm`

En Pydantic v2, el método `from_orm()` fue eliminado. Usar `model_validate()`:

```python
# INCORRECTO (Pydantic v1)
user_response = UserResponse.from_orm(user_orm)

# CORRECTO (Pydantic v2)
user_response = UserResponse.model_validate(user_orm)
```

### Validators: `@field_validator` reemplaza `@validator`

```python
# INCORRECTO (Pydantic v1)
from pydantic import validator

class CreateUserRequest(BaseModel):
    email: str
    
    @validator('email')
    def email_must_be_lowercase(cls, v):
        return v.lower()

# CORRECTO (Pydantic v2)
from pydantic import field_validator

class CreateUserRequest(BaseModel):
    email: str
    
    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower()
```

---

## 10. PostgreSQL Específico

### UUID vs String: consistencia entre backend y frontend

**Convención del proyecto**: El backend usa `UUID` nativo de Python/PostgreSQL. El frontend recibe y envía UUIDs como `string` (TypeScript no tiene tipo UUID nativo). Esta conversión la maneja FastAPI/Pydantic automáticamente, pero hay que tener cuidado en tests:

```python
# En tests de integración: comparar como string
assert response.json()["data"]["id"] == str(user.id)  # correcto
assert response.json()["data"]["id"] == user.id       # puede fallar (UUID vs str)
```

### JSONB vs JSON

El proyecto usa `JSONB` (no `JSON`) para todos los campos de contenido variable (p.ej. `CognitiveTraceRecord.content`). `JSONB` es binario, indexable, y más eficiente para consultas. `JSON` conserva whitespace y orden original — no lo usamos.

```python
# Siempre JSONB en modelos SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

class CognitiveTraceRecord(Base):
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
```

---

## 11. Anthropic API

### Streaming y manejo de errores

El tutor socrático usa streaming de la API de Anthropic para una experiencia más fluida. El streaming requiere manejo específico de errores: si la conexión se corta a la mitad, el mensaje puede quedar truncado.

```python
# Siempre usar try/finally para limpiar el estado si el stream falla
async def stream_tutor_response(prompt: str):
    try:
        async with anthropic_client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        # Loguear el error y enviar mensaje de fallback al usuario
        logger.error(f"Anthropic API error: {e}")
        yield "Lo siento, hubo un problema. Intentá de nuevo."
```

### Rate limits y costos

La API de Anthropic tiene rate limits por minuto y por día. En desarrollo, usar el modelo más pequeño posible (`claude-haiku-3-5`) para pruebas que no involucren calidad de respuesta. Usar `claude-opus-4-5` solo para tests de calidad del tutor.

Configurar `ANTHROPIC_MODEL` en `.env` según el contexto:
- Desarrollo: `claude-haiku-3-5`
- Testing de calidad: `claude-opus-4-5`
- Producción: `claude-opus-4-5` (definir en variables de entorno de deploy)

---

## 12. Testing Async

### `pytest-asyncio` requiere `asyncio_mode = "auto"` o `@pytest.mark.asyncio`

Sin configuración, los tests async de pytest no corren como coroutines:

```python
# INCORRECTO: el test pasa sin ejecutar el cuerpo async
async def test_create_user(session):
    user = await create_user(session, CreateUserRequest(...))
    assert user.id is not None
```

**Solución**: Ya está configurado en `pyproject.toml` con `asyncio_mode = "auto"`. Si por algún motivo esto no aplica:

```python
import pytest

@pytest.mark.asyncio
async def test_create_user(session):
    user = await create_user(session, CreateUserRequest(...))
    assert user.id is not None
```

### El event loop debe ser el mismo para toda la suite

Usar `asyncio_mode = "auto"` con `scope = "session"` para el event loop:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
```

Esto evita el error `Event loop is closed` que ocurre cuando fixtures de distintos scopes usan event loops diferentes.
