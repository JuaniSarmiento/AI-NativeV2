# Guía de Desarrollo — Plataforma AI-Native

**UTN FRM | Sistema Pedagógico para Enseñanza de Programación**
Última actualización: 2026-04-10
Versión: 1.0

---

## Índice

1. [Filosofía del Proyecto](#1-filosofía-del-proyecto)
2. [Arquitectura en un Vistazo](#2-arquitectura-en-un-vistazo)
3. [Backend: Guía Práctica](#3-backend-guía-práctica)
   - [Cómo agregar un nuevo módulo de feature](#31-cómo-agregar-un-nuevo-módulo-de-feature)
   - [Cómo agregar un nuevo endpoint](#32-cómo-agregar-un-nuevo-endpoint)
   - [Cómo agregar un schema Pydantic](#33-cómo-agregar-un-schema-pydantic)
   - [Cómo escribir una migración de Alembic](#34-cómo-escribir-una-migración-de-alembic)
   - [Cómo escribir tests](#35-cómo-escribir-tests)
4. [Frontend: Guía Práctica](#4-frontend-guía-práctica)
   - [Cómo agregar un nuevo feature folder](#41-cómo-agregar-un-nuevo-feature-folder)
   - [Cómo crear un store de Zustand](#42-cómo-crear-un-store-de-zustand)
   - [Cómo agregar una nueva página/ruta](#43-cómo-agregar-una-nueva-pánginaruta)
   - [Cómo trabajar con MSW mocks](#44-cómo-trabajar-con-msw-mocks)
   - [Cómo escribir tests de frontend](#45-cómo-escribir-tests-de-frontend)
5. [Transversal: Dominio Pedagógico](#5-transversal-dominio-pedagógico)
   - [Cómo agregar un nuevo tipo de evento cognitivo](#51-cómo-agregar-un-nuevo-tipo-de-evento-cognitivo)
   - [Cómo modificar el system prompt del tutor](#52-cómo-modificar-el-system-prompt-del-tutor)
   - [Cómo agregar una nueva regla de negocio](#53-cómo-agregar-una-nueva-regla-de-negocio)
6. [Referencias Rápidas](#6-referencias-rápidas)

---

## 1. Filosofía del Proyecto

### Domain-Driven: el dominio pedagógico manda

La Plataforma AI-Native no es un CRUD genérico. Es la implementación de un modelo teórico (N4) para una tesis doctoral. Cada componente técnico existe porque un constructo pedagógico lo requiere.

**Antes de agregar cualquier feature, responder las 5 preguntas de validación de coherencia:**

1. ¿Qué constructo de la tesis justifica este componente?
2. ¿Qué evidencia produce o consume?
3. ¿En qué tabla queda persistida?
4. ¿Qué endpoint habilita su operación?
5. ¿Cómo impacta en la evaluación?

Si alguna pregunta no puede responderse con precisión, existe una brecha de alineación. No implementar hasta resolverla.

### Thesis-Aligned: el código debe ser auditable

El CTR (Cognitive Trace Record) es el artefacto central. Cada acción del alumno debe traducirse en evidencia pedagógica con semántica explícita. No hay "logs genéricos" — hay eventos cognitivos clasificados.

Esto implica:
- **No registrar datos sin significado pedagógico** (RN-2).
- **No emitir evaluaciones sin evidencia en el CTR** (RN-1).
- **No modificar el CTR post-cierre** (RN-7).
- **No dar soluciones directas desde el tutor** (RN-6).

### Process Over Product

La plataforma evalúa el **proceso** cognitivo, no solo el resultado del código. Esto se refleja en el código: el sistema de snapshots, el registro de interacciones con el tutor, el hash chain del CTR — todo existe para capturar el proceso, no solo el output final.

### Propiedad de Schemas

Cada fase es **dueña exclusiva** de su schema de base de datos. Esta regla no es solo convención — tiene consecuencias en permisos de PostgreSQL y en cómo los servicios se comunican.

```
EPIC 0 + 1 → dueños de operational
EPIC 2     → dueño de governance (comparte operational para tutor_interactions)
EPIC 3     → dueño de cognitive + analytics
EPIC 4     → no escribe en ningún schema directamente
```

---

## 2. Arquitectura en un Vistazo

### Capas del Backend

```
HTTP Request
    │
    ▼ [Router] — valida JWT, deserializa con Pydantic, delega al service
    │
    ▼ [Service] — lógica de negocio, orquesta repos, emite eventos de dominio
    │
    ▼ [Repository] — queries SQL via SQLAlchemy, devuelve modelos ORM
    │
    ▼ [SQLAlchemy Model] — mapeo a PostgreSQL
```

**Reglas estrictas:**
- El Router NO tiene lógica de negocio.
- El Service NO importa tipos de FastAPI (`Request`, `Response`, `HTTPException`).
- El Repository NO tiene lógica de negocio.
- Las excepciones de dominio (`DomainException`) se lanzan en el Service, el Router las convierte en `HTTPException`.

### Estructura del Frontend

```
features/{nombre}/
├── components/   → UI pura, recibe props, sin llamadas API directas
├── hooks/        → Lógica de UI, orquesta store + api
├── store/        → Estado Zustand 5, acciones, selectores
├── api/          → Funciones async que llaman al backend (sin estado)
└── types.ts      → Interfaces TypeScript del dominio
```

### Comunicación entre Dominios

- **Fase 1 → Fase 3**: vía Redis Streams (eventos `SubmissionCreated`, `TutorInteractionCompleted`).
- **Fase 2 → Fase 3**: vía Redis Streams.
- **Fase 3 lee Fase 1**: vía `GET /api/v1/exercises/{id}` (REST interno, no import directo).
- **Fase 4 → Backend**: vía REST + WebSocket.

Ver `knowledge-base/02-arquitectura/01_arquitectura_general.md` para el diagrama completo.

---

## 3. Backend: Guía Práctica

### 3.1 Cómo Agregar un Nuevo Módulo de Feature

Seguir este orden estrictamente. Cada capa depende de la anterior.

**Orden**: Model → Migration → Repository → Service → Router → Tests

#### Paso 1: Definir el modelo SQLAlchemy

```python
# backend/app/shared/models/operational.py
from sqlalchemy import String, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import text
from datetime import datetime, UTC
from uuid import UUID

class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = {"schema": "operational"}  # SIEMPRE especificar el schema

    # PK: UUID generado por la DB
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Campos del dominio
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_taxonomy: Mapped[dict] = mapped_column(JSONB, nullable=True)
    starter_code: Mapped[str] = mapped_column(Text, nullable=True)
    test_cases: Mapped[list] = mapped_column(JSONB, nullable=True)

    # Timestamps estándar (en TODOS los modelos)
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

    # Soft delete (en la mayoría de modelos, excepto cognitive_events)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # FK a otra tabla
    course_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("operational.courses.id"),
        nullable=False,
    )
```

#### Paso 2: Generar y revisar la migración de Alembic

```bash
cd backend
source .venv/bin/activate

# Auto-generar
alembic revision --autogenerate -m "add_exercises_table_to_operational"

# OBLIGATORIO: revisar el archivo generado
# Verificar que:
# 1. El schema es correcto (schema='operational')
# 2. Los índices esperados están presentes
# 3. No hay operaciones no deseadas (DROP TABLE inesperado, etc.)
cat alembic/versions/xxxx_add_exercises_table_to_operational.py

# Aplicar
alembic upgrade head

# Verificar estado
alembic current
```

**Ejemplo de migración completa revisada:**

```python
# alembic/versions/003_add_exercises_table.py
def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("topic_taxonomy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("starter_code", sa.Text(), nullable=True),
        sa.Column("test_cases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["operational.courses.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="operational",
    )
    # Índices para queries frecuentes
    op.create_index("ix_exercises_course_id", "exercises", ["course_id"], schema="operational")
    op.create_index("ix_exercises_difficulty", "exercises", ["difficulty"], schema="operational")

def downgrade() -> None:
    op.drop_index("ix_exercises_difficulty", table_name="exercises", schema="operational")
    op.drop_index("ix_exercises_course_id", table_name="exercises", schema="operational")
    op.drop_table("exercises", schema="operational")
```

#### Paso 3: Implementar el Repository

```python
# backend/app/shared/repositories/exercise_repo.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.shared.models.operational import Exercise

class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, exercise: Exercise) -> Exercise:
        self.session.add(exercise)
        await self.session.flush()  # flush, no commit — el UoW maneja el commit
        await self.session.refresh(exercise)
        return exercise

    async def find_by_id(self, exercise_id: UUID) -> Exercise | None:
        result = await self.session.execute(
            select(Exercise).where(
                Exercise.id == exercise_id,
                Exercise.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def find_all_active(
        self,
        course_id: UUID | None = None,
        difficulty: int | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Exercise], int]:
        query = select(Exercise).where(Exercise.is_active.is_(True))

        if course_id is not None:
            query = query.where(Exercise.course_id == course_id)
        if difficulty is not None:
            query = query.where(Exercise.difficulty == difficulty)

        # Contar total sin paginación
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Paginación
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def soft_delete(self, exercise_id: UUID) -> bool:
        exercise = await self.find_by_id(exercise_id)
        if exercise is None:
            return False
        exercise.is_active = False
        exercise.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return True
```

#### Paso 4: Implementar el Service

```python
# backend/app/features/exercises/service.py
import math
from uuid import UUID
from app.core.exceptions import ExerciseNotFoundError, ExerciseForbiddenError, InvalidDifficultyError
from app.shared.repositories.exercise_repo import ExerciseRepository
from app.shared.models.operational import Exercise, User
from app.features.exercises.schemas import (
    CreateExerciseRequest, UpdateExerciseRequest,
    ExerciseResponse, PaginatedExercisesResponse,
)

class ExerciseService:
    def __init__(self, repository: ExerciseRepository) -> None:
        self.repository = repository

    async def create_exercise(
        self,
        request: CreateExerciseRequest,
        current_user: User,
    ) -> ExerciseResponse:
        """Crea un ejercicio. Solo docentes y admins pueden crear ejercicios."""
        exercise = Exercise(
            title=request.title,
            description=request.description,
            difficulty=request.difficulty,
            topic_taxonomy=request.topic_taxonomy,
            starter_code=request.starter_code,
            test_cases=[tc.model_dump() for tc in request.test_cases],
            course_id=request.course_id,
        )
        created = await self.repository.create(exercise)
        return ExerciseResponse.model_validate(created)

    async def get_exercise(self, exercise_id: UUID) -> ExerciseResponse:
        exercise = await self.repository.find_by_id(exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(f"Exercise {exercise_id} not found")
        return ExerciseResponse.model_validate(exercise)

    async def list_exercises(
        self,
        course_id: UUID | None = None,
        difficulty: int | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedExercisesResponse:
        if difficulty is not None and difficulty not in range(1, 5):
            raise InvalidDifficultyError(f"Difficulty must be 1-4, got {difficulty}")

        exercises, total = await self.repository.find_all_active(
            course_id=course_id,
            difficulty=difficulty,
            page=page,
            per_page=per_page,
        )
        return PaginatedExercisesResponse(
            items=[ExerciseResponse.model_validate(e) for e in exercises],
            total=total,
            page=page,
            per_page=per_page,
            pages=math.ceil(total / per_page) if total > 0 else 0,
        )

    async def soft_delete_exercise(self, exercise_id: UUID, current_user: User) -> None:
        exercise = await self.repository.find_by_id(exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(f"Exercise {exercise_id} not found")
        # Solo el creador o admin puede borrar
        if exercise.course_id != current_user.managed_course_id and current_user.role != "admin":
            raise ExerciseForbiddenError("You don't own this exercise")
        await self.repository.soft_delete(exercise_id)
```

#### Paso 5: Implementar el Router

```python
# backend/app/features/exercises/router.py
from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.core.dependencies import get_current_user, require_role
from app.features.exercises.service import ExerciseService
from app.features.exercises.schemas import (
    CreateExerciseRequest, UpdateExerciseRequest,
    ExerciseResponse, PaginatedExercisesResponse,
)
from app.shared.schemas.responses import SuccessResponse
from app.shared.models.operational import User

router = APIRouter(prefix="/exercises", tags=["exercises"])

def get_exercise_service(session=Depends(get_db)) -> ExerciseService:
    from app.shared.repositories.exercise_repo import ExerciseRepository
    return ExerciseService(ExerciseRepository(session))

@router.get(
    "/",
    response_model=SuccessResponse[PaginatedExercisesResponse],
    summary="Listar ejercicios activos",
)
async def list_exercises(
    course_id: UUID | None = Query(default=None, description="Filtrar por curso"),
    difficulty: int | None = Query(default=None, ge=1, le=4, description="Nivel 1-4"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[PaginatedExercisesResponse]:
    result = await service.list_exercises(
        course_id=course_id,
        difficulty=difficulty,
        page=page,
        per_page=per_page,
    )
    return SuccessResponse(data=result)

@router.post(
    "/",
    response_model=SuccessResponse[ExerciseResponse],
    status_code=201,
    summary="Crear ejercicio (docente/admin)",
    dependencies=[Depends(require_role("docente"))],
)
async def create_exercise(
    request: CreateExerciseRequest,
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ExerciseResponse]:
    exercise = await service.create_exercise(request, current_user)
    return SuccessResponse(data=exercise)

@router.get(
    "/{exercise_id}",
    response_model=SuccessResponse[ExerciseResponse],
    summary="Obtener ejercicio por ID",
)
async def get_exercise(
    exercise_id: UUID,
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ExerciseResponse]:
    exercise = await service.get_exercise(exercise_id)
    return SuccessResponse(data=exercise)

@router.delete(
    "/{exercise_id}",
    status_code=204,
    summary="Eliminar ejercicio (soft delete)",
)
async def delete_exercise(
    exercise_id: UUID,
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.soft_delete_exercise(exercise_id, current_user)
```

#### Paso 6: Registrar el Router en main.py

```python
# backend/app/main.py
from app.features.exercises.router import router as exercises_router

app.include_router(exercises_router, prefix="/api/v1")
```

---

### 3.2 Cómo Agregar un Nuevo Endpoint

Para agregar un endpoint a un módulo existente:

1. **Definir el schema de request/response** en `schemas.py` si no existe.
2. **Agregar el método al Service** con la lógica de negocio.
3. **Agregar el método al Repository** si necesita nueva query.
4. **Agregar el decorador en el Router**.
5. **Agregar tests** (unit del service + integration del endpoint).

**Ejemplo**: agregar `PATCH /exercises/{id}` para actualización parcial:

```python
# En schemas.py:
class UpdateExerciseRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=4)
    topic_taxonomy: dict | None = None

# En service.py:
async def update_exercise(
    self,
    exercise_id: UUID,
    request: UpdateExerciseRequest,
    current_user: User,
) -> ExerciseResponse:
    exercise = await self.repository.find_by_id(exercise_id)
    if exercise is None:
        raise ExerciseNotFoundError(...)
    # Actualizar solo los campos provistos (PATCH semántico)
    if request.title is not None:
        exercise.title = request.title
    if request.description is not None:
        exercise.description = request.description
    if request.difficulty is not None:
        exercise.difficulty = request.difficulty
    await self.session.flush()
    return ExerciseResponse.model_validate(exercise)

# En router.py:
@router.patch(
    "/{exercise_id}",
    response_model=SuccessResponse[ExerciseResponse],
    summary="Actualizar ejercicio (parcial)",
)
async def update_exercise(
    exercise_id: UUID,
    request: UpdateExerciseRequest,
    service: ExerciseService = Depends(get_exercise_service),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ExerciseResponse]:
    updated = await service.update_exercise(exercise_id, request, current_user)
    return SuccessResponse(data=updated)
```

---

### 3.3 Cómo Agregar un Schema Pydantic

Los schemas siguen una jerarquía de herencia. **No romper esta convención.**

```python
# backend/app/features/exercises/schemas.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Literal

# 1. Base: campos compartidos entre request y response
class ExerciseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    difficulty: int = Field(..., ge=1, le=4, description="Nivel de dificultad 1-4")

# 2. Request de creación
class TestCaseSchema(BaseModel):
    description: str
    input: str
    expected_output: str
    is_visible: bool = True

class CreateExerciseRequest(ExerciseBase):
    course_id: UUID
    topic_taxonomy: dict | None = None
    starter_code: str | None = None
    test_cases: list[TestCaseSchema] = Field(default_factory=list)
    constraints: str | None = None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: int) -> int:
        if v not in range(1, 5):
            raise ValueError("Difficulty must be between 1 and 4")
        return v

# 3. Request de actualización (todos los campos opcionales)
class UpdateExerciseRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=4)
    topic_taxonomy: dict | None = None

# 4. Response (from_attributes para validar desde el ORM)
class ExerciseResponse(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    topic_taxonomy: dict | None = None
    starter_code: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

# 5. Response paginado
class PaginatedExercisesResponse(BaseModel):
    items: list[ExerciseResponse]
    total: int
    page: int
    per_page: int
    pages: int

# 6. Params de filtrado
class ExerciseFilterParams(BaseModel):
    course_id: UUID | None = None
    difficulty: int | None = Field(default=None, ge=1, le=4)
    q: str | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
```

**Convenciones de naming de schemas:**

| Patrón | Uso |
|--------|-----|
| `XBase` | Campos compartidos |
| `CreateXRequest` | Payload para POST |
| `UpdateXRequest` | Payload para PATCH (todos opcionales) |
| `XResponse` | Respuesta de objeto único |
| `PaginatedXResponse` | Respuesta paginada |
| `XFilterParams` | Query params de filtrado |

---

### 3.4 Cómo Escribir una Migración de Alembic

#### Migración automática (caso más común)

```bash
# 1. Modificar el modelo SQLAlchemy primero
# 2. Generar la migración
cd backend
alembic revision --autogenerate -m "descripcion_del_cambio"

# 3. SIEMPRE revisar el archivo generado
# Buscar operaciones inesperadas (DROP, ALTER sin querer, etc.)

# 4. Aplicar en desarrollo
alembic upgrade head

# 5. Verificar
alembic current  # debe mostrar el revision ID más reciente
```

#### Migración manual (para cambios complejos)

```python
# alembic/versions/005_add_computed_columns.py
"""Add epistemic_quality_score column to cognitive_metrics.

Revision ID: abc123def456
Revises: 789xyz012
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = '789xyz012'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Agregar columna con valor default para no romper registros existentes
    op.add_column(
        'cognitive_metrics',
        sa.Column(
            'epistemic_quality_score',
            sa.Float(),
            nullable=True,  # nullable=True primero para compatibilidad con datos existentes
            comment='Calidad Epistémica (Qe): constructo jerárquico sobre N1-N4'
        ),
        schema='cognitive'
    )

    # Si se necesita un valor default para registros existentes:
    op.execute(
        "UPDATE cognitive.cognitive_metrics SET epistemic_quality_score = 0.0 WHERE epistemic_quality_score IS NULL"
    )

    # Luego hacer not null si corresponde
    op.alter_column(
        'cognitive_metrics',
        'epistemic_quality_score',
        nullable=False,
        schema='cognitive'
    )

    # Crear índice si la columna se usará en queries frecuentes
    op.create_index(
        'ix_cognitive_metrics_qe_score',
        'cognitive_metrics',
        ['epistemic_quality_score'],
        schema='cognitive'
    )

def downgrade() -> None:
    op.drop_index('ix_cognitive_metrics_qe_score', table_name='cognitive_metrics', schema='cognitive')
    op.drop_column('cognitive_metrics', 'epistemic_quality_score', schema='cognitive')
```

#### Reglas de Migraciones

- **Nunca editar una migración ya aplicada en un branch compartido.** Crear una nueva.
- **Las migraciones deben ser reversibles** (`downgrade()` funcional).
- **Migrar en orden**: nunca aplicar una migración de un schema que depende de otra sin antes aplicar la dependencia.
- **Soft delete**: al borrar tablas, preferir `is_active=false` en lugar de `DROP TABLE`.

---

### 3.5 Cómo Escribir Tests

#### Tests unitarios (sin DB, sin red)

```python
# backend/tests/unit/test_exercise_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.features.exercises.service import ExerciseService
from app.features.exercises.schemas import CreateExerciseRequest
from app.core.exceptions import ExerciseNotFoundError, InvalidDifficultyError

# El formato de nombre es: test_{qué}_{condición}
@pytest.mark.unit
class TestExerciseService:

    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        repo.create = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=None)
        repo.find_all_active = AsyncMock(return_value=([], 0))
        repo.soft_delete = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        return ExerciseService(mock_repo)

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        user.role = "docente"
        return user

    async def test_create_exercise_calls_repo_with_correct_data(self, service, mock_repo, mock_user):
        # Arrange
        request = CreateExerciseRequest(
            title="Fibonacci iterativo",
            description="Implementar Fibonacci de forma iterativa",
            difficulty=2,
            course_id=uuid4(),
        )

        # Act
        await service.create_exercise(request, mock_user)

        # Assert
        mock_repo.create.assert_called_once()
        called_with = mock_repo.create.call_args[0][0]
        assert called_with.title == "Fibonacci iterativo"
        assert called_with.difficulty == 2

    async def test_get_exercise_not_found_raises_error(self, service, mock_repo):
        # Arrange
        mock_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ExerciseNotFoundError):
            await service.get_exercise(uuid4())

    async def test_list_exercises_with_invalid_difficulty_raises_error(self, service):
        with pytest.raises(InvalidDifficultyError):
            await service.list_exercises(difficulty=5)

    async def test_list_exercises_with_valid_difficulty_calls_repo(self, service, mock_repo):
        await service.list_exercises(difficulty=2)
        mock_repo.find_all_active.assert_called_once_with(
            course_id=None, difficulty=2, page=1, per_page=20
        )
```

#### Tests de integración (con PostgreSQL real via testcontainers)

```python
# backend/tests/integration/test_exercise_router.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
class TestExerciseRouterIntegration:

    async def test_create_exercise_returns_201(
        self, client: AsyncClient, auth_headers_docente: dict
    ):
        payload = {
            "title": "Bubble Sort implementación",
            "description": "Implementar el algoritmo bubble sort de forma eficiente",
            "difficulty": 3,
            "course_id": str(seeded_course_id),
        }

        response = await client.post(
            "/api/v1/exercises",
            json=payload,
            headers=auth_headers_docente,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["title"] == "Bubble Sort implementación"
        assert data["data"]["difficulty"] == 3
        assert "id" in data["data"]

    async def test_list_exercises_without_auth_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/exercises")
        assert response.status_code == 401

    async def test_create_exercise_as_alumno_returns_403(
        self, client: AsyncClient, auth_headers_alumno: dict
    ):
        payload = {"title": "Test", "description": "Test description", "difficulty": 1, "course_id": str(uuid4())}
        response = await client.post("/api/v1/exercises", json=payload, headers=auth_headers_alumno)
        assert response.status_code == 403

    async def test_list_exercises_filters_by_difficulty(
        self, client: AsyncClient, auth_headers: dict, seeded_exercises: list
    ):
        response = await client.get("/api/v1/exercises?difficulty=2", headers=auth_headers)

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert all(item["difficulty"] == 2 for item in items)
```

**Fixtures en `conftest.py`** — ver `knowledge-base/05-dx/06_estrategia_de_testing.md` para el setup completo con testcontainers.

---

## 4. Frontend: Guía Práctica

### 4.1 Cómo Agregar un Nuevo Feature Folder

Cada feature tiene la misma estructura interna. Seguir este patrón sin excepción.

```bash
mkdir -p frontend/src/features/mi-feature/{components,hooks,store,api}
touch frontend/src/features/mi-feature/types.ts
```

Estructura resultante:

```
features/mi-feature/
├── components/
│   ├── MiComponente.tsx
│   └── MiComponente.test.tsx
├── hooks/
│   └── useMiFeature.ts
├── store/
│   └── miFeatureStore.ts
├── api/
│   └── miFeatureApi.ts
└── types.ts
```

**Reglas**:
- Un componente por archivo. Nombre del archivo = nombre del componente.
- Los componentes no hacen llamadas directas a la API. Usan hooks que orquestan store + api.
- Los hooks son el punto de coordinación: llaman a la api y actualizan el store.
- La capa `api/` solo tiene funciones async puras sin estado.

---

### 4.2 Cómo Crear un Store de Zustand

```typescript
// frontend/src/features/exercises/store/exerciseStore.ts
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Exercise, ExerciseFilters } from '../types'

// 1. Definir la interfaz del estado separada de las acciones
interface ExerciseState {
  exercises: Exercise[]
  currentExercise: Exercise | null
  filters: ExerciseFilters
  isLoading: boolean
  error: string | null
}

// 2. Definir las acciones separadas del estado
interface ExerciseActions {
  setExercises: (exercises: Exercise[]) => void
  setCurrentExercise: (exercise: Exercise | null) => void
  setFilters: (filters: Partial<ExerciseFilters>) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetFilters: () => void
  reset: () => void
}

type ExerciseStore = ExerciseState & ExerciseActions

// 3. Estado inicial separado para reseteos
const INITIAL_STATE: ExerciseState = {
  exercises: [],
  currentExercise: null,
  filters: { page: 1, perPage: 20 },
  isLoading: false,
  error: null,
}

// 4. Crear el store con devtools para debugging
export const useExerciseStore = create<ExerciseStore>()(
  devtools(
    (set) => ({
      ...INITIAL_STATE,

      setExercises: (exercises) => set({ exercises }, false, 'setExercises'),
      setCurrentExercise: (exercise) => set({ currentExercise: exercise }, false, 'setCurrentExercise'),

      // Al cambiar filtros, resetear la página para evitar resultados stale
      setFilters: (newFilters) =>
        set(
          (state) => ({
            filters: { ...state.filters, ...newFilters, page: 1 },
          }),
          false,
          'setFilters'
        ),

      setLoading: (isLoading) => set({ isLoading }, false, 'setLoading'),
      setError: (error) => set({ error }, false, 'setError'),
      resetFilters: () => set({ filters: INITIAL_STATE.filters }, false, 'resetFilters'),
      reset: () => set(INITIAL_STATE, false, 'reset'),
    }),
    { name: 'ExerciseStore' }  // nombre visible en Redux DevTools
  )
)

// 5. Selectores memoizados con useShallow para evitar re-renders innecesarios
// Importar así en los hooks: useShallow de 'zustand/react/shallow'

// Uso correcto con useShallow:
// const { exercises, isLoading } = useExerciseStore(
//   useShallow((state) => ({ exercises: state.exercises, isLoading: state.isLoading }))
// )

// Uso incorrecto (causa re-renders en cada cambio del store):
// const exercises = useExerciseStore((state) => state.exercises)
// const isLoading = useExerciseStore((state) => state.isLoading)
```

**Cuándo usar `persist` middleware:**

```typescript
import { persist } from 'zustand/middleware'

// Solo para estado que debe sobrevivir un refresh de página:
// - authStore (token de acceso, datos del usuario)
// - preferencias de UI (tema, tamaño de font del editor)

// NO persistir:
// - exerciseStore (datos del servidor, se rehidrata con una llamada)
// - tutorStore (mensajes de una sesión activa)
// - cognitiveStore (datos de análisis del servidor)
```

---

### 4.3 Cómo Agregar una Nueva Página/Ruta

```typescript
// 1. Crear el componente de la página
// frontend/src/features/exercises/components/ExercisePage.tsx
import type { FC } from 'react'
import { useParams } from 'react-router'
import { useExercise } from '../hooks/useExercise'
import { MonacoEditor } from './MonacoEditor'
import { TutorChat } from '@/features/tutor/components/TutorChat'

export const ExercisePage: FC = () => {
  const { exerciseId } = useParams<{ exerciseId: string }>()
  const { exercise, isLoading, error } = useExercise(exerciseId!)

  if (isLoading) return <div className="flex items-center justify-center h-screen">Cargando...</div>
  if (error) return <div className="text-red-500">Error: {error}</div>
  if (!exercise) return null

  return (
    <div className="flex h-screen">
      {/* Panel izquierdo: enunciado */}
      <div className="w-1/3 p-4 border-r overflow-y-auto">
        <h1 className="text-xl font-bold">{exercise.title}</h1>
        {/* markdown renderer */}
      </div>

      {/* Panel central: editor */}
      <div className="flex-1">
        <MonacoEditor exerciseId={exercise.id} starterCode={exercise.starterCode} />
      </div>

      {/* Panel derecho: tutor + output */}
      <div className="w-1/3 border-l">
        <TutorChat exerciseId={exercise.id} />
      </div>
    </div>
  )
}
```

```typescript
// 2. Registrar la ruta en App.tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router'
import { PrivateRoute } from '@/shared/components/PrivateRoute'
import { ExercisePage } from '@/features/exercises/components/ExercisePage'
import { StudentDashboard } from '@/features/student/components/StudentDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Rutas protegidas */}
        <Route element={<PrivateRoute />}>
          <Route path="/dashboard" element={<StudentDashboard />} />
          <Route path="/exercises/:exerciseId" element={<ExercisePage />} />
        </Route>

        {/* Rutas solo para docente */}
        <Route element={<PrivateRoute requiredRole="docente" />}>
          <Route path="/teacher/dashboard" element={<TeacherDashboard />} />
          <Route path="/teacher/students/:studentId/trace" element={<CognitiveTracePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

```typescript
// 3. Crear el PrivateRoute component
// frontend/src/shared/components/PrivateRoute.tsx
import { Navigate, Outlet } from 'react-router'
import { useAuthStore } from '@/features/auth/store/authStore'

interface PrivateRouteProps {
  requiredRole?: 'alumno' | 'docente' | 'admin'
}

export function PrivateRoute({ requiredRole }: PrivateRouteProps) {
  const { user, accessToken } = useAuthStore()

  if (!accessToken || !user) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user.role !== requiredRole && user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
```

---

### 4.4 Cómo Trabajar con MSW Mocks

```typescript
// frontend/src/mocks/handlers/exercises.ts
import { http, HttpResponse, delay } from 'msw'
import type { PaginatedExercisesResponse, ExerciseResponse } from '@shared/types/api'

export const exercisesHandlers = [
  // GET /api/v1/exercises
  http.get('/api/v1/exercises', async ({ request }) => {
    await delay(300)  // simular latencia realista

    const url = new URL(request.url)
    const difficulty = url.searchParams.get('difficulty')
    const page = Number(url.searchParams.get('page') ?? 1)

    const allExercises: ExerciseResponse[] = [
      {
        id: '550e8400-e29b-41d4-a716-446655440001',
        title: 'Fibonacci iterativo',
        description: 'Implementar la serie de Fibonacci de forma iterativa...',
        difficulty: 2,
        isActive: true,
        courseId: '550e8400-e29b-41d4-a716-446655440000',
        createdAt: '2026-04-01T10:00:00Z',
        updatedAt: '2026-04-01T10:00:00Z',
      },
      // ... más ejercicios
    ]

    const filtered = difficulty
      ? allExercises.filter(e => e.difficulty === Number(difficulty))
      : allExercises

    const perPage = 20
    const items = filtered.slice((page - 1) * perPage, page * perPage)

    const response: PaginatedExercisesResponse = {
      items,
      total: filtered.length,
      page,
      perPage,
      pages: Math.ceil(filtered.length / perPage),
    }

    return HttpResponse.json({ status: 'ok', data: response })
  }),

  // GET /api/v1/exercises/:id
  http.get('/api/v1/exercises/:exerciseId', async ({ params }) => {
    await delay(200)
    // retornar ejercicio por ID desde datos mock
    return HttpResponse.json({
      status: 'ok',
      data: MOCK_EXERCISES[params.exerciseId as string] ?? null
    })
  }),

  // Simular error 429 para testing de rate limit
  http.post('/api/v1/exercises/:id/run', async () => {
    if (Math.random() < 0.05) {  // 5% de probabilidad de error para testing
      return HttpResponse.json(
        { status: 'error', errors: [{ code: 'TUTOR_RATE_LIMIT_EXCEEDED', message: 'Rate limit exceeded' }] },
        { status: 429 }
      )
    }
    await delay(800)  // simular ejecución en sandbox
    return HttpResponse.json({ status: 'ok', data: MOCK_RUN_RESULT })
  }),
]
```

```typescript
// frontend/src/mocks/browser.ts
import { setupWorker } from 'msw/browser'
import { exercisesHandlers } from './handlers/exercises'
import { tutorHandlers } from './handlers/tutor'
import { cognitiveHandlers } from './handlers/cognitive'

export const worker = setupWorker(
  ...exercisesHandlers,
  ...tutorHandlers,
  ...cognitiveHandlers,
)
```

```typescript
// frontend/src/main.tsx
async function main() {
  // Activar MSW solo en desarrollo
  if (import.meta.env.DEV && import.meta.env.VITE_MSW_ENABLED !== 'false') {
    const { worker } = await import('./mocks/browser')
    await worker.start({
      onUnhandledRequest: 'warn',  // advertir en consola si hay requests no mockeados
    })
  }

  createRoot(document.getElementById('root')!).render(<App />)
}

main()
```

**Para desactivar MSW cuando el endpoint real esté listo:**

```env
# .env.local
VITE_MSW_ENABLED=false
```

No requiere ningún cambio de código en los componentes.

---

### 4.5 Cómo Escribir Tests de Frontend

#### Tests de stores (Vitest)

```typescript
// frontend/src/features/exercises/store/exerciseStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useExerciseStore } from './exerciseStore'

describe('useExerciseStore', () => {
  // Resetear el store antes de cada test para aislamiento
  beforeEach(() => {
    useExerciseStore.getState().reset()
  })

  describe('setFilters', () => {
    it('should reset page to 1 when difficulty filter changes', () => {
      const { result } = renderHook(() => useExerciseStore())

      act(() => { result.current.setFilters({ page: 5 }) })
      act(() => { result.current.setFilters({ difficulty: 2 }) })

      expect(result.current.filters.page).toBe(1)
      expect(result.current.filters.difficulty).toBe(2)
    })

    it('should preserve other filters when updating one', () => {
      const { result } = renderHook(() => useExerciseStore())

      act(() => { result.current.setFilters({ difficulty: 3 }) })
      act(() => { result.current.setFilters({ perPage: 50 }) })

      // difficulty no se perdió al cambiar perPage
      expect(result.current.filters.difficulty).toBe(3)
      expect(result.current.filters.perPage).toBe(50)
    })
  })

  describe('resetFilters', () => {
    it('should clear all filters and reset to defaults', () => {
      const { result } = renderHook(() => useExerciseStore())

      act(() => { result.current.setFilters({ difficulty: 2, page: 3 }) })
      act(() => { result.current.resetFilters() })

      expect(result.current.filters.difficulty).toBeUndefined()
      expect(result.current.filters.page).toBe(1)
    })
  })
})
```

#### Tests de componentes (Vitest + Testing Library)

```typescript
// frontend/src/features/exercises/components/ExerciseCard.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExerciseCard } from './ExerciseCard'
import type { Exercise } from '../types'

const mockExercise: Exercise = {
  id: 'test-id',
  title: 'Fibonacci iterativo',
  description: 'Implementar Fibonacci...',
  difficulty: 2,
  isActive: true,
  courseId: 'course-id',
  createdAt: '2026-04-01',
  updatedAt: '2026-04-01',
}

describe('ExerciseCard', () => {
  it('renders exercise title and difficulty', () => {
    render(<ExerciseCard exercise={mockExercise} onClick={vi.fn()} />)

    expect(screen.getByText('Fibonacci iterativo')).toBeInTheDocument()
    expect(screen.getByText('Nivel 2')).toBeInTheDocument()
  })

  it('calls onClick when card is clicked', async () => {
    const handleClick = vi.fn()
    const { user } = render(<ExerciseCard exercise={mockExercise} onClick={handleClick} />)

    await user.click(screen.getByRole('article'))

    expect(handleClick).toHaveBeenCalledWith(mockExercise.id)
  })

  it('shows inactive badge when exercise is not active', () => {
    render(<ExerciseCard exercise={{ ...mockExercise, isActive: false }} onClick={vi.fn()} />)
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
  })
})
```

#### Tests E2E (Playwright)

```typescript
// frontend/e2e/exercise-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Flujo completo de ejercicio', () => {
  test.beforeEach(async ({ page }) => {
    // Login directo via API para evitar repetir el flujo en cada test
    const response = await page.request.post('/api/v1/auth/login', {
      data: { email: 'alumno1@utn.edu.ar', password: 'alumno123dev' },
    })
    const { data } = await response.json()
    await page.context().addCookies([/* o usar localStorage */])
    await page.goto('/dashboard')
  })

  test('alumno puede ejecutar código y ver output', async ({ page }) => {
    // Navegar a un ejercicio
    await page.click('[data-testid="exercise-card"]:first-child')

    // Esperar que el editor cargue
    await expect(page.locator('.monaco-editor')).toBeVisible()

    // Hacer click en Ejecutar
    await page.click('[data-testid="run-button"]')

    // Esperar el resultado
    await expect(page.locator('[data-testid="output-panel"]')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Test 1:')).toBeVisible()
  })

  test('alumno no puede ver ejercicios de otros cursos', async ({ page }) => {
    const response = await page.request.get('/api/v1/exercises?course_id=otro-course-id')
    expect(response.status()).toBe(403)
  })
})
```

---

## 5. Transversal: Dominio Pedagógico

### 5.1 Cómo Agregar un Nuevo Tipo de Evento Cognitivo

Los `event_type` son el vocabulario canónico del sistema. Agregar uno nuevo requiere coordinación entre Fase 3 (clasificador) y Fase 2 (tutor que lo genera).

**Proceso obligatorio:**

1. **Actualizar el mapeo canónico** en `knowledge-base/01-negocio/04_reglas_de_negocio.md`:

```markdown
| event_type | Nivel N4 |
|-----------|---------|
| reads_problem | N1 |
| ... (existentes) ... |
| nuevo_event_type | N2 |  ← agregar aquí con justificación pedagógica
```

2. **Actualizar el enum en el modelo SQLAlchemy**:

```python
# backend/app/shared/models/cognitive.py
import enum

class CognitiveEventType(str, enum.Enum):
    READS_PROBLEM = "reads_problem"
    ASKS_CLARIFICATION = "asks_clarification"
    REFORMULATES_PROBLEM = "reformulates_problem"
    DEFINES_STRATEGY = "defines_strategy"
    CHANGES_STRATEGY = "changes_strategy"
    ASKS_HINT = "asks_hint"
    RUNS_TEST = "runs_test"
    INTERPRETS_ERROR = "interprets_error"
    FIXES_ERROR = "fixes_error"
    ASKS_EXPLANATION = "asks_explanation"
    AUDITS_AI_SUGGESTION = "audits_ai_suggestion"
    # NUEVO:
    COMPARES_STRATEGIES = "compares_strategies"  # N2: el alumno compara dos enfoques

class N4Level(str, enum.Enum):
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    N4 = "N4"
```

3. **Crear la migración de Alembic** para agregar el valor al enum PostgreSQL:

```python
# alembic/versions/XXX_add_compares_strategies_event_type.py
def upgrade() -> None:
    op.execute("ALTER TYPE cognitive.cognitive_event_type ADD VALUE IF NOT EXISTS 'compares_strategies'")

def downgrade() -> None:
    # Los enum values de PostgreSQL no pueden removerse con ALTER TYPE
    # La reversión requiere DROP TYPE + CREATE TYPE (costoso)
    pass
```

4. **Actualizar el CognitiveEventClassifier** con el nuevo mapeo:

```python
# backend/app/features/cognitive/classifier.py
EVENT_TO_N4_LEVEL: dict[CognitiveEventType, N4Level] = {
    CognitiveEventType.READS_PROBLEM: N4Level.N1,
    CognitiveEventType.ASKS_CLARIFICATION: N4Level.N1,
    CognitiveEventType.REFORMULATES_PROBLEM: N4Level.N1,
    CognitiveEventType.DEFINES_STRATEGY: N4Level.N2,
    CognitiveEventType.CHANGES_STRATEGY: N4Level.N2,
    CognitiveEventType.ASKS_HINT: N4Level.N2,
    CognitiveEventType.COMPARES_STRATEGIES: N4Level.N2,  # NUEVO
    CognitiveEventType.RUNS_TEST: N4Level.N3,
    CognitiveEventType.INTERPRETS_ERROR: N4Level.N3,
    CognitiveEventType.FIXES_ERROR: N4Level.N3,
    CognitiveEventType.ASKS_EXPLANATION: N4Level.N4,
    CognitiveEventType.AUDITS_AI_SUGGESTION: N4Level.N4,
}
```

5. **Actualizar el frontend** si el nuevo event_type necesita mostrarse en la traza cognitiva:

```typescript
// frontend/src/features/cognitive/types.ts
export const N4_EVENT_COLORS = {
  N1: '#3B82F6',  // azul
  N2: '#10B981',  // verde
  N3: '#F59E0B',  // naranja
  N4: '#8B5CF6',  // violeta
} as const

export const EVENT_TYPE_LABELS: Record<string, string> = {
  reads_problem: 'Leyó el enunciado',
  asks_clarification: 'Pidió aclaración',
  // ... agregar:
  compares_strategies: 'Comparó estrategias',  // NUEVO
}
```

6. **Agregar tests** en el clasificador:

```python
def test_compares_strategies_maps_to_n2():
    assert EVENT_TO_N4_LEVEL[CognitiveEventType.COMPARES_STRATEGIES] == N4Level.N2
```

---

### 5.2 Cómo Modificar el System Prompt del Tutor

El system prompt del tutor es un artefacto de gobernanza. **No se modifica directamente en código** — se gestiona a través del endpoint de administración y el sistema de versionado.

**Proceso obligatorio:**

1. **Redactar el nuevo prompt** en un documento aparte con justificación pedagógica (referenciando el modelo N4 y el documento maestro empate3).

2. **Verificar que cumple las restricciones** del guardrail antes de activar:
   - No debe dar instrucciones que contradigan el principio socrático.
   - Debe incluir instrucciones explícitas para NO dar soluciones directas.
   - Debe tener instrucciones para adaptar el nivel de guía al del alumno.

3. **Correr los tests adversariales** con el nuevo prompt en entorno de staging:

```bash
# Activar el nuevo prompt en staging
ANTHROPIC_API_KEY=xxx pytest tests/adversarial/ -v -m adversarial
```

4. **Activar via API** (requiere rol admin):

```bash
# Crear la nueva versión del prompt
curl -X POST http://localhost:8000/api/v1/admin/tutor/system-prompts \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "prompt_text": "...",
    "notes": "Ajuste: agregar instrucciones para ejercicios de debugging. Referencia: empate3 §4.3"
  }'

# Activar la nueva versión (desactiva la anterior automáticamente)
curl -X PATCH http://localhost:8000/api/v1/admin/tutor/system-prompts/{id}/activate \
  -H "Authorization: Bearer <admin-token>"
```

5. **Verificar que se registró el governance_event** de `prompt_update`.

**Regla de versionado semver para prompts:**
- `MAJOR.0.0`: modifica el constructo N4 (requiere revisión formal con tesis).
- `X.MINOR.0`: modifica la pedagogía operativa (requiere aprobación del responsable institucional).
- `X.Y.PATCH`: ajuste de refinamiento (fundamentación escrita en las notas del prompt).

---

### 5.3 Cómo Agregar una Nueva Regla de Negocio

Las reglas de negocio del dominio son no negociables — violarlas rompe la coherencia del modelo N4.

**Proceso:**

1. **Documentar la regla** en `knowledge-base/01-negocio/04_reglas_de_negocio.md`:

```markdown
### RN-9: No hay repetición de evaluación sin nuevo CTR

Un alumno que quiera ser re-evaluado en un ejercicio debe generar un nuevo CTR completo.
No se puede emitir una nueva evaluación sobre el mismo CTR.

- **Enforcement**: EvaluationEngine verifica que la sesión asociada es nueva
- **Violación**: Re-evaluar usando datos de una sesión ya evaluada
- **Impacto**: Contamina la trazabilidad — el CTR original ya fue usado para una evaluación formal
```

2. **Implementar el enforcement** en el Service correspondiente:

```python
# backend/app/features/evaluation/service.py
async def evaluate_student(self, student_id: UUID, exercise_id: UUID, session_id: UUID) -> EvaluationResult:
    # Verificar RN-9: no hay repetición de evaluación sin nuevo CTR
    existing_evaluation = await self.evaluation_repo.find_by_session(session_id)
    if existing_evaluation is not None:
        raise EvaluationAlreadyExistsError(
            f"Session {session_id} has already been evaluated. "
            "A new cognitive session is required for re-evaluation (RN-9)."
        )
    # ... continuar con la evaluación
```

3. **Agregar un test** que verifica la regla:

```python
@pytest.mark.unit
async def test_evaluate_already_evaluated_session_raises_error(service, mock_repo):
    """RN-9: No hay repetición de evaluación sin nuevo CTR."""
    mock_repo.find_by_session.return_value = existing_evaluation

    with pytest.raises(EvaluationAlreadyExistsError):
        await service.evaluate_student(student_id, exercise_id, already_evaluated_session_id)
```

4. **Referenciar la regla** en el comentario del código:

```python
# RN-9: verificar que no existe evaluación previa para esta sesión
existing = await self.repo.find_by_session(session_id)
if existing:
    raise EvaluationAlreadyExistsError(...)
```

---

## 6. Referencias Rápidas

### Comandos más usados en desarrollo

```bash
# Backend
cd backend
source .venv/bin/activate

python -m pytest tests/unit/ -v                 # solo tests unitarios
python -m pytest tests/integration/ -v          # solo tests integración
python -m pytest tests/ -v --cov=app --cov-report=term-missing  # con coverage

ruff check .                                     # linter
ruff format .                                    # formatter
mypy app/                                        # type checker

alembic revision --autogenerate -m "descripcion" # nueva migración
alembic upgrade head                             # aplicar migraciones
alembic downgrade -1                             # rollback una migración
alembic current                                  # estado actual

python scripts/seed.py                           # datos de prueba

# Frontend
cd frontend
npm run dev                                      # servidor de desarrollo
npm run test                                     # tests interactivos
npm run test:run                                 # tests una vez (CI)
npm run test:coverage                            # tests con coverage
npm run lint                                     # ESLint
npm run format                                   # Prettier
npm run build                                    # build de producción
npx playwright test                              # tests E2E
```

### Estructura de errores del dominio

```python
# backend/app/core/exceptions.py

# Clase base
class DomainException(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code  # UPPERCASE_SNAKE — ver error_codes.py

# Subclases por dominio
class ExerciseNotFoundError(DomainException):
    def __init__(self, message: str):
        super().__init__(message, code="EXERCISE_NOT_FOUND")

class ExerciseForbiddenError(DomainException):
    def __init__(self, message: str):
        super().__init__(message, code="EXERCISE_FORBIDDEN")

class CTRHashChainBrokenError(DomainException):
    def __init__(self, message: str):
        super().__init__(message, code="CTR_HASH_CHAIN_BROKEN")

# El Router convierte DomainException → HTTPException
@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    status_map = {
        "EXERCISE_NOT_FOUND": 404,
        "EXERCISE_FORBIDDEN": 403,
        "CTR_HASH_CHAIN_BROKEN": 409,
        # ...
    }
    return JSONResponse(
        status_code=status_map.get(exc.code, 500),
        content={"status": "error", "errors": [{"code": exc.code, "message": str(exc)}]},
    )
```

### Wrapper de respuesta estándar

Todos los endpoints usan:

```python
# Respuesta exitosa
return SuccessResponse(data=resultado)
# → {"status": "ok", "data": {...}}

# Respuesta paginada
return SuccessResponse(
    data=PaginatedXResponse(items=[...], total=100, page=1, per_page=20, pages=5),
    meta={"query_time_ms": 45}
)
# → {"status": "ok", "data": {"items": [...], "total": 100, ...}, "meta": {...}}
```

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0 | UTN FRM*
