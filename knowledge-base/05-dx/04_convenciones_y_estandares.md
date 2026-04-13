# Convenciones y Estándares

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Estas convenciones son **obligatorias** para todos los desarrolladores del proyecto. Su objetivo es garantizar coherencia en el código, facilitar code reviews, y hacer que el proyecto sea mantenible a largo plazo. Ante cualquier duda, la convención en este documento tiene prioridad.

---

## Indice

1. [Nombrado de Archivos](#1-nombrado-de-archivos)
2. [Nombrado de Variables y Funciones](#2-nombrado-de-variables-y-funciones)
3. [Schemas Pydantic](#3-schemas-pydantic)
4. [Modelos SQLAlchemy](#4-modelos-sqlalchemy)
5. [Endpoints de la API](#5-endpoints-de-la-api)
6. [Códigos de Error](#6-códigos-de-error)
7. [Git — Commits y Branches](#7-git--commits-y-branches)
8. [Organización del Código](#8-organización-del-código)
9. [Imports](#9-imports)
10. [Type Hints](#10-type-hints)
11. [Comentarios y Docstrings](#11-comentarios-y-docstrings)
12. [Tests](#12-tests)

---

## 1. Nombrado de Archivos

### Backend (Python)

Todo en `snake_case.py`. La estructura es **feature-based** dentro de `app/features/`:

```
backend/app/
├── features/
│   ├── auth/
│   │   ├── router.py           # NO: authRouter.py — un router por feature dentro de su carpeta
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── courses/
│   │   └── ...
│   ├── exercises/
│   │   └── ...
│   ├── sandbox/
│   │   └── ...
│   ├── tutor/
│   │   └── ...
│   ├── cognitive/
│   │   └── ...
│   ├── evaluation/
│   │   └── ...
│   └── governance/
│       └── ...
├── shared/
│   ├── db/
│   ├── models/
│   ├── repositories/
│   └── schemas/
└── tests/
    ├── test_auth_service.py    # siempre con prefijo test_
    └── test_exercise_router.py
```

### Frontend (TypeScript/React)

- Componentes React: `PascalCase.tsx`
- Hooks: `camelCase.ts` con prefijo `use`
- Stores: `camelCase.ts` con sufijo `Store`
- Utilidades: `camelCase.ts`
- Tipos: `camelCase.ts` o junto al módulo que los usa
- Tests: `NombreArchivo.test.ts` o `NombreArchivo.test.tsx`
- Specs E2E: `nombre-feature.spec.ts`

```
frontend/src/
├── components/
│   ├── TutorChat.tsx           # PascalCase
│   ├── ExerciseCard.tsx
│   └── ui/
│       ├── Button.tsx
│       └── Modal.tsx
├── stores/
│   ├── authStore.ts            # camelCase + sufijo Store
│   ├── exerciseStore.ts
│   └── tutorStore.ts
├── hooks/
│   ├── useAuth.ts              # camelCase + prefijo use
│   ├── useExercises.ts
│   └── useTutorSession.ts
├── api/
│   ├── authApi.ts              # camelCase + sufijo Api
│   └── exerciseApi.ts
└── types/
    ├── auth.ts                 # camelCase
    └── exercise.ts
```

---

## 2. Nombrado de Variables y Funciones

### Python — snake_case

```python
# Variables
user_id = UUID("...")
exercise_count = 10
is_authenticated = True
created_at = datetime.now(UTC)

# Funciones
def get_user_by_id(user_id: UUID) -> User: ...
def create_cognitive_event(data: CreateCTRRequest) -> CognitiveEvent: ...
def validate_hash_chain(records: list[CognitiveEvent]) -> bool: ...

# Métodos de clase
class UserRepository:
    async def find_by_email(self, email: str) -> User | None: ...
    async def find_all_active(self, page: int, per_page: int) -> list[User]: ...
    async def soft_delete(self, user_id: UUID) -> None: ...

# Constantes del módulo: UPPER_SNAKE_CASE
MAX_LOGIN_ATTEMPTS = 5
DEFAULT_PAGE_SIZE = 20
HASH_ALGORITHM = "sha256"
```

### TypeScript — camelCase

```typescript
// Variables
const userId = '...'
const exerciseCount = 10
const isAuthenticated = true

// Funciones
function getUserById(userId: string): Promise<User> { ... }
function createTutorSession(exerciseId: string): Promise<TutorSession> { ... }

// Métodos
class ExerciseService {
  async findByDifficulty(difficulty: number): Promise<Exercise[]> { ... }
  async softDelete(exerciseId: string): Promise<void> { ... }
}

// Constantes: UPPER_SNAKE_CASE para valores de configuración y enums-like
const MAX_RECONNECT_ATTEMPTS = 5
const DEFAULT_PAGE_SIZE = 20

// Enums: PascalCase con valores PascalCase
enum ExerciseDifficulty {
  Beginner = 1,
  Intermediate = 2,
  Advanced = 3,
  Expert = 4,
}
```

### Reglas de nombrado de funciones

| Tipo de operación | Prefijo preferido | Ejemplo |
|---|---|---|
| Lectura única | `get_` | `get_user_by_id` |
| Lectura múltiple | `find_all_`, `list_` | `find_all_active_exercises` |
| Creación | `create_` | `create_user` |
| Actualización parcial | `update_` | `update_exercise_title` |
| Reemplazo total | `replace_` | `replace_user_roles` |
| Eliminación lógica | `soft_delete_` | `soft_delete_exercise` |
| Eliminación física | `delete_` | `delete_expired_tokens` |
| Verificación booleana | `is_`, `has_`, `can_` | `is_token_expired`, `has_permission` |
| Validación (lanza o retorna bool) | `validate_` | `validate_hash_chain` |
| Cálculo | `compute_`, `calculate_` | `compute_ctr_hash` |
| Transformación | `to_`, `from_`, `map_` | `to_response_schema` |

---

## 3. Schemas Pydantic

### Jerarquía de herencia

```python
# Base: campos comunes compartidos entre request y response
class ExerciseBase(BaseModel):
    title: str
    description: str
    difficulty: int

# Request de creación: hereda de Base, agrega campos específicos de creación
class CreateExerciseRequest(ExerciseBase):
    topic_id: UUID
    expected_complexity: str | None = None

# Request de actualización: todos los campos opcionales (PATCH semántico)
class UpdateExerciseRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: int | None = None

# Response: hereda de Base, agrega IDs, timestamps, campos computados
class ExerciseResponse(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool
    topic: TopicResponse | None = None  # relación expandida

# Response paginado: wrapper genérico
class PaginatedExercisesResponse(BaseModel):
    items: list[ExerciseResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
```

### Convenciones de nombres

| Patrón | Uso |
|---|---|
| `XBase` | Campos compartidos entre request/response |
| `CreateXRequest` | Payload para POST de creación |
| `UpdateXRequest` | Payload para PATCH (todos opcionales) |
| `ReplaceXRequest` | Payload para PUT (todos requeridos) |
| `XResponse` | Respuesta de un objeto único |
| `XListResponse` | Respuesta de una lista de objetos |
| `PaginatedXResponse` | Respuesta paginada |
| `XFilterParams` | Query params de filtrado |

### Wrapper de respuesta estándar

Todos los endpoints usan el mismo wrapper de respuesta:

```python
class SuccessResponse(BaseModel, Generic[T]):
    status: Literal["ok"] = "ok"
    data: T
    meta: dict[str, Any] | None = None

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    errors: list[ErrorDetail]
    meta: dict[str, Any] | None = None

class ErrorDetail(BaseModel):
    code: str       # UPPERCASE_SNAKE: "EXERCISE_NOT_FOUND"
    message: str    # Mensaje legible por humanos
    field: str | None = None  # Campo específico si es error de validación
```

---

## 4. Modelos SQLAlchemy

### Convenciones

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

class Base(DeclarativeBase):
    pass

# Singular, PascalCase — NO plural
class User(Base):                     # NO: Users, user, USERS
    __tablename__ = "users"           # plural en la tabla
    __table_args__ = {"schema": "operational"}  # SIEMPRE especificar schema
    
    # PK siempre UUID, server_default para generación en DB
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    
    # Timestamps estándar en todos los modelos
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=datetime.now(UTC),
        nullable=False,
    )
    
    # Soft delete: is_active + deleted_at
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # EXCEPCIÓN: los modelos del CTR (cognitive_events, code_snapshots, governance_events)
    # NO tienen is_active ni deleted_at — son inmutables por diseño (hash chain).
```

### Nombres de tablas y columnas

```python
# Tablas: plural, snake_case, en el schema correcto
__tablename__ = "cognitive_events"   # NO: CognitiveEvent, ctr
__table_args__ = {"schema": "cognitive"}

# Columnas: snake_case, descriptivo
user_id: Mapped[UUID]           # NO: userId, uid
exercise_id: Mapped[UUID]       # FK con sufijo _id
cognitive_level: Mapped[int]    # descriptivo
is_active: Mapped[bool]         # booleanos con prefijo is_/has_/can_

# Índices: ix_{tabla}_{columna(s)}
Index("ix_users_email", User.email, unique=True)
Index("ix_ctrs_user_created", CognitiveEvent.user_id, CognitiveEvent.created_at)
```

---

## 5. Endpoints de la API

### Estructura de URLs

```
/api/v1/{resource-plural}                    # colección
/api/v1/{resource-plural}/{id}               # elemento específico
/api/v1/{resource-plural}/{id}/{sub-resource} # sub-recurso
/api/v1/{resource-plural}/{id}/actions/{verb} # acciones no-CRUD
```

Ejemplos concretos del proyecto:

```
GET    /api/v1/exercises                    # listar ejercicios (paginado)
POST   /api/v1/exercises                    # crear ejercicio
GET    /api/v1/exercises/{exercise_id}      # obtener ejercicio
PATCH  /api/v1/exercises/{exercise_id}      # actualizar ejercicio (parcial)
DELETE /api/v1/exercises/{exercise_id}      # soft delete

GET    /api/v1/exercises/{exercise_id}/sessions          # sesiones de un ejercicio
POST   /api/v1/exercises/{exercise_id}/sessions          # iniciar sesión

POST   /api/v1/exercises/{exercise_id}/sessions/{session_id}/messages  # enviar mensaje al tutor
GET    /api/v1/exercises/{exercise_id}/sessions/{session_id}/ctr       # obtener CTRs de la sesión

POST   /api/v1/auth/login                   # acción de login (verbo como sub-path)
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
POST   /api/v1/auth/reset-password

GET    /api/v1/users/me                     # endpoint especial "me"
PATCH  /api/v1/users/me
```

### HTTP Methods y semántica

| Método | Uso | Idempotente | Body |
|---|---|---|---|
| `GET` | Leer datos | Sí | No |
| `POST` | Crear recurso, acciones | No | Sí |
| `PUT` | Reemplazar recurso completo | Sí | Sí |
| `PATCH` | Actualizar campos específicos | No | Sí |
| `DELETE` | Eliminar recurso (soft) | Sí | No |

### Status codes

| Situación | Código |
|---|---|
| Lectura exitosa | `200 OK` |
| Creación exitosa | `201 Created` |
| Acción exitosa sin contenido | `204 No Content` |
| Validación fallida | `422 Unprocessable Entity` |
| No autenticado | `401 Unauthorized` |
| Sin permisos | `403 Forbidden` |
| No encontrado | `404 Not Found` |
| Conflicto (email duplicado) | `409 Conflict` |
| Rate limit excedido | `429 Too Many Requests` |
| Error interno | `500 Internal Server Error` |

### Query params de paginación y filtrado

```
GET /api/v1/exercises?page=1&per_page=20&difficulty=2&topic_id=uuid&is_active=true&q=fibonacci
```

- `page`: número de página, default 1, mínimo 1
- `per_page`: elementos por página, default 20, máximo 100
- `q`: búsqueda full-text cuando aplica
- Filtros específicos de cada recurso se documentan en el schema `XFilterParams`

---

## 6. Códigos de Error

Los códigos de error son strings en `UPPERCASE_SNAKE_CASE`, agrupados por dominio:

```python
# Auth
AUTH_INVALID_CREDENTIALS     = "AUTH_INVALID_CREDENTIALS"
AUTH_TOKEN_EXPIRED           = "AUTH_TOKEN_EXPIRED"
AUTH_TOKEN_INVALID           = "AUTH_TOKEN_INVALID"
AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
AUTH_MAX_ATTEMPTS_EXCEEDED   = "AUTH_MAX_ATTEMPTS_EXCEEDED"

# Recursos genéricos
RESOURCE_NOT_FOUND           = "RESOURCE_NOT_FOUND"
RESOURCE_ALREADY_EXISTS      = "RESOURCE_ALREADY_EXISTS"
RESOURCE_SOFT_DELETED        = "RESOURCE_SOFT_DELETED"

# Ejercicios
EXERCISE_NOT_FOUND           = "EXERCISE_NOT_FOUND"
EXERCISE_INVALID_DIFFICULTY  = "EXERCISE_INVALID_DIFFICULTY"

# Sesiones de tutor
TUTOR_SESSION_NOT_FOUND      = "TUTOR_SESSION_NOT_FOUND"
TUTOR_SESSION_ALREADY_CLOSED = "TUTOR_SESSION_ALREADY_CLOSED"
TUTOR_RATE_LIMIT_EXCEEDED    = "TUTOR_RATE_LIMIT_EXCEEDED"

# CTR / Hash chain
CTR_HASH_CHAIN_BROKEN        = "CTR_HASH_CHAIN_BROKEN"
CTR_IMMUTABLE_VIOLATION      = "CTR_IMMUTABLE_VIOLATION"

# Validación
VALIDATION_REQUIRED_FIELD    = "VALIDATION_REQUIRED_FIELD"
VALIDATION_INVALID_FORMAT    = "VALIDATION_INVALID_FORMAT"
VALIDATION_OUT_OF_RANGE      = "VALIDATION_OUT_OF_RANGE"

# Sistema
INTERNAL_SERVER_ERROR        = "INTERNAL_SERVER_ERROR"
SERVICE_UNAVAILABLE          = "SERVICE_UNAVAILABLE"
```

Definidos centralmente en `backend/app/core/error_codes.py`.

---

## 7. Git — Commits y Branches

### Conventional Commits

El formato es obligatorio. Los commits que no sigan este formato serán rechazados por el pre-commit hook:

```
<tipo>(<alcance>): <descripción corta en infinitivo>

[cuerpo opcional: qué y por qué, no cómo]

[footer opcional: BREAKING CHANGE, Refs: #issue]
```

**Tipos válidos**:

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad visible para el usuario |
| `fix` | Corrección de bug |
| `refactor` | Refactoring sin cambio de comportamiento |
| `test` | Agregar o modificar tests |
| `docs` | Documentación únicamente |
| `chore` | Tareas de mantenimiento (deps, config, CI) |
| `perf` | Mejora de rendimiento |
| `ci` | Cambios en CI/CD |
| `build` | Cambios en el sistema de build |
| `revert` | Revertir un commit anterior |

**Alcances válidos** (scope):

```
auth, user, exercise, tutor, ctr, hash-chain, session,
analytics, sandbox, websocket, db, api, frontend, infra
```

**Ejemplos correctos**:

```
feat(exercise): add difficulty filter to exercise list endpoint
fix(auth): prevent token reuse after logout
refactor(tutor): extract prompt builder to separate module
test(hash-chain): add adversarial tests for chain integrity
chore(deps): update anthropic SDK to v0.40.0
docs(onboarding): add WSL2 setup instructions
perf(db): add composite index on ctr user_id+created_at
```

**Ejemplos incorrectos**:

```
Fixed bug           # No tipo, no alcance
feat: stuff         # Descripción no informativa
FEAT(AUTH): Add login  # Tipo en mayúsculas
feat(auth): Added login  # Pasado, no infinitivo
```

### Branching — GitHub Flow

```
main
├── feat/exercise-difficulty-filter     # feature
├── fix/auth-token-refresh-race         # bug fix
├── refactor/tutor-service-extract      # refactoring
├── test/adversarial-tutor-prompts      # solo tests
├── chore/update-anthropic-sdk          # mantenimiento
└── docs/onboarding-guide               # documentación
```

Reglas:
- `main` es la rama de producción. Siempre debe estar deployable.
- Las branches se crean desde `main`, siempre.
- El nombre de la branch sigue el patrón `{tipo}/{descripcion-corta-en-kebab}`.
- Al completar la feature: PR hacia `main`, requiere 1 review + CI verde.
- No hay ramas de release ni develop. GitHub Flow puro.
- Las branches se borran después del merge.

---

## 8. Organización del Código

### Backend — Arquitectura en capas

```
Routers (HTTP/WS)
    ↓ validan request con Pydantic, llaman al service
Services (lógica de negocio)
    ↓ orquestan repositorios, llaman a APIs externas
Repositories (acceso a datos)
    ↓ queries SQL via SQLAlchemy
Models (SQLAlchemy ORM)
    ↓ mapeo a PostgreSQL
```

**Un router por feature** (`auth_router.py`, `exercise_router.py`, `tutor_router.py`):

```python
# Thin router: NO lógica de negocio aquí
@router.post("/", response_model=SuccessResponse[ExerciseResponse], status_code=201)
async def create_exercise(
    request: CreateExerciseRequest,
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ExerciseResponse]:
    exercise = await service.create_exercise(request, current_user)
    return SuccessResponse(data=ExerciseResponse.model_validate(exercise))
```

**Un service por feature** (`exercise_service.py`): toda la lógica de negocio aquí.

**Un repository por modelo** (`exercise_repository.py`): queries a la base de datos, sin lógica de negocio.

### Frontend — Feature folders

```
src/
├── features/
│   ├── auth/
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   └── LogoutButton.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   ├── stores/
│   │   │   └── authStore.ts
│   │   ├── api/
│   │   │   └── authApi.ts
│   │   └── types.ts
│   ├── student/         # Dashboard alumno, vista ejercicio, reflexión
│   │   └── ...
│   ├── teacher/         # Dashboard docente, traza cognitiva, reportes
│   │   └── ...
│   ├── exercise/        # Monaco editor, ejecución, submission
│   │   └── ...
│   └── shared/          # Componentes compartidos entre features
│       └── ...
├── shared/
│   ├── components/
│   │   ├── Button.tsx
│   │   └── Modal.tsx
│   ├── hooks/
│   │   └── useDebounce.ts
│   └── utils/
│       └── formatDate.ts
└── app/
    ├── router.tsx
    └── App.tsx
```

---

## 9. Imports

### Python — orden de imports (enforced por ruff/isort)

```python
# 1. Standard library
import hashlib
import json
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# 3. Módulos locales del proyecto
from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.models.exercise_model import Exercise
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise_schemas import CreateExerciseRequest, ExerciseResponse
```

### TypeScript — orden de imports

```typescript
// 1. React y librerías de terceros
import { useState, useEffect } from 'react'
import { useShallow } from 'zustand/react/shallow'

// 2. Tipos de terceros
import type { FC, ReactNode } from 'react'

// 3. Módulos locales — features
import { useExerciseStore } from '@/features/exercises/stores/exerciseStore'
import { fetchExercises } from '@/features/exercises/api/exerciseApi'
import type { Exercise } from '@/features/exercises/types'

// 4. Módulos locales — shared
import { Button } from '@/shared/components/Button'
import { formatDate } from '@/shared/utils/formatDate'
```

---

## 10. Type Hints

### Python — estricto y obligatorio

```python
# OBLIGATORIO: type hints en todas las firmas de función
# INCORRECTO
def get_user(user_id):
    ...

# CORRECTO
async def get_user(user_id: UUID) -> User | None:
    ...

# Union types: usar X | Y (Python 3.10+ syntax), no Optional[X]
def find_by_email(email: str) -> User | None: ...  # NO: Optional[User]

# Listas y dicts genéricos: lowercase (Python 3.9+ syntax)
def get_all_exercises() -> list[Exercise]: ...     # NO: List[Exercise]
def get_config() -> dict[str, Any]: ...            # NO: Dict[str, Any]

# Literales
def set_status(status: Literal["active", "inactive"]) -> None: ...

# TypeVar para generics
T = TypeVar("T")
def paginate(items: list[T], page: int) -> PaginatedResponse[T]: ...
```

### TypeScript — strict mode

```typescript
// tsconfig.json tiene "strict": true — NUNCA deshabilitar

// OBLIGATORIO: tipar todos los parámetros y retornos de funciones
// INCORRECTO
function getUser(id) {
  return fetch(`/users/${id}`)
}

// CORRECTO
async function getUser(id: string): Promise<User> {
  const response = await fetch(`/api/v1/users/${id}`)
  return response.json()
}

// No usar `any` — usar `unknown` si el tipo es realmente desconocido
function handleApiError(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Error desconocido'
}

// Interfaces para objetos de dominio, types para unions/intersections
interface Exercise {
  id: string
  title: string
  difficulty: ExerciseDifficulty
}

type ExerciseStatus = 'pending' | 'in_progress' | 'completed'
```

---

## 11. Comentarios y Docstrings

### Python

```python
# Docstrings en servicios y funciones públicas importantes
async def compute_cognitive_score(
    ctr_records: list[CognitiveEvent],
    rubric: ScoringRubric,
) -> CognitiveScore:
    """
    Calcula el puntaje cognitivo N1-N4 basado en los registros de traza.
    
    El algoritmo aplica la rúbrica del modelo N4 (Ver: empate3 §3.2) a los
    eventos cognitivos registrados en los CTR. Retorna un puntaje con
    desglose por dimensión (N1: comprensión, N2: estrategia, N3: validación,
    N4: interacción con IA).
    
    Args:
        ctr_records: Lista de CTR de la sesión a evaluar.
        rubric: Rúbrica de scoring cargada desde governance schema.
    
    Returns:
        CognitiveScore con puntaje total y desglose por nivel N1-N4.
    
    Raises:
        EmptyCTRListError: Si ctr_records está vacío.
        InvalidRubricError: Si la rúbrica no tiene todos los niveles configurados.
    """
```

Comentarios inline: solo cuando el código no es auto-explicativo. El código debe ser legible sin comentarios en casos normales.

```python
# Bien: explica el por qué de una decisión no obvia
# Usar sorted keys para garantizar determinismo en el hash
serialized = json.dumps(payload, sort_keys=True)

# Mal: describe el qué (obvio del código)
# Incrementar el contador
counter += 1
```

### TypeScript

```typescript
/**
 * Selector memoizado para obtener ejercicios filtrados por dificultad.
 * Usar useShallow para evitar re-renders cuando otros campos del store cambian.
 */
const useExercisesByDifficulty = (difficulty: number) =>
  useExerciseStore(
    useShallow((state) => state.exercises.filter((e) => e.difficulty === difficulty))
  )
```

---

## 12. Tests

### Nomenclatura

```python
# Formato: test_{qué se testea}_{condición o contexto}
def test_create_user_with_valid_data_returns_user(): ...
def test_create_user_with_duplicate_email_raises_conflict(): ...
def test_login_with_invalid_credentials_returns_401(): ...
def test_hash_chain_with_tampered_record_fails_validation(): ...
```

### Estructura AAA (Arrange, Act, Assert)

```python
async def test_create_exercise_returns_created_exercise(session, test_user):
    # Arrange
    request = CreateExerciseRequest(
        title="Fibonacci",
        description="Implementar Fibonacci iterativo",
        difficulty=2,
    )
    service = ExerciseService(session)
    
    # Act
    exercise = await service.create_exercise(request, test_user)
    
    # Assert
    assert exercise.id is not None
    assert exercise.title == "Fibonacci"
    assert exercise.is_active is True
    assert exercise.created_at is not None
```

### Fixtures en conftest.py

Las fixtures compartidas van en `tests/conftest.py` (o en conftest.py del subdirectorio si son específicas de unit/integration). No duplicar fixtures entre archivos.
