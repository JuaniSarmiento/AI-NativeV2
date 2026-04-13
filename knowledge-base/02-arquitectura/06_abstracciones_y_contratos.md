# 06 — Abstracciones y Contratos entre Componentes

**Plataforma AI-Native — UTN FRM — Documentación de Arquitectura**
**Versión:** 1.0 | **Estado:** Vigente | **Alcance:** Transversal — todos los módulos

---

## Tabla de Contenidos

1. [Filosofía de Contratos en el Monolito Modular](#1-filosofía-de-contratos-en-el-monolito-modular)
2. [OpenAPI como Fuente de Verdad](#2-openapi-como-fuente-de-verdad)
3. [Reglas de Propiedad de Schemas](#3-reglas-de-propiedad-de-schemas)
4. [Response Wrapper Estándar](#4-response-wrapper-estándar)
5. [Pydantic Schemas como DTOs de Contrato](#5-pydantic-schemas-como-dtos-de-contrato)
6. [Tipos TypeScript Auto-generados desde OpenAPI](#6-tipos-typescript-auto-generados-desde-openapi)
7. [LLM Adapter Protocol](#7-llm-adapter-protocol)
8. [Repository Base Class](#8-repository-base-class)
9. [Unit of Work Abstraction](#9-unit-of-work-abstraction)
10. [Jerarquía de Excepciones de Dominio](#10-jerarquía-de-excepciones-de-dominio)
11. [Contratos de Servicios entre Módulos](#11-contratos-de-servicios-entre-módulos)
12. [Invariantes y Reglas de Negocio](#12-invariantes-y-reglas-de-negocio)

---

## 1. Filosofía de Contratos en el Monolito Modular

La plataforma AI-Native es un **monolito modular**: un único proceso Python con módulos claramente delimitados por dominio (phase1, phase2, phase3, phase4, shared). A diferencia de microservicios, los módulos comparten el mismo proceso pero se comunican a través de **interfaces explícitas**, no llamadas directas a implementaciones internas.

### 1.1 Principios de Diseño de Contratos

**1. Cada módulo expone una interfaz pública y oculta su implementación.**
Los servicios externos al módulo solo pueden invocar métodos definidos en la interfaz. Acceder directamente al repositorio interno de otro módulo está prohibido por convención y enforcement de linters.

**2. El schema de datos lo define y mantiene el módulo propietario.**
Si Phase 3 necesita datos de Phase 1, los solicita vía REST usando la ruta definida en el contrato OpenAPI de Phase 1. Phase 3 no escribe en las tablas de Phase 1.

**3. Los contratos son versionados.**
Cambios breaking en un contrato requieren un nuevo endpoint (`/v2/`) y un período de deprecación de al menos un sprint.

**4. Las abstracciones retrasan el acoplamiento, no lo eliminan.**
El objetivo no es "desacoplar todo" sino desacoplar las partes que tienen razones independientes de cambio.

### 1.2 Límites de Módulos

```
app/
├── features/
│   ├── auth/           # Autenticación, JWT, RBAC
│   ├── courses/        # Cursos, comisiones, inscripciones
│   ├── exercises/      # Ejercicios, submissions, snapshots
│   ├── sandbox/        # Ejecución aislada de código
│   ├── tutor/          # Tutor socrático IA, streaming WS
│   ├── cognitive/      # Clasificación cognitiva, CTR, hash chain
│   ├── evaluation/     # Motor de evaluación N4
│   └── governance/     # Gobernanza, prompts, auditoría
├── core/               # Excepciones, logging, event bus
└── shared/             # DB session, UoW, models, repositories base
```

**Regla de dependencias (unidireccional):**
```
auth, courses, exercises, sandbox, tutor → shared (operational schema)
cognitive, evaluation → shared (cognitive schema, consume eventos via event bus)
governance → shared (governance schema)
NUNCA: exercises importa de cognitive directamente, etc.
```

---

## 2. OpenAPI como Fuente de Verdad

FastAPI genera automáticamente el schema OpenAPI 3.1 en `/openapi.json`. Este schema es **la única fuente de verdad** para:

- Tipos TypeScript generados para el frontend.
- Documentación de contratos entre módulos.
- Tests de contrato (contract testing).
- Generación de clientes HTTP para integraciones externas.

### 2.1 Acceso al Schema

```bash
# En desarrollo
curl http://localhost:8000/openapi.json | python -m json.tool

# Generar tipos TypeScript (automatizado en CI)
npx openapi-typescript http://localhost:8000/openapi.json \
  --output src/types/api.generated.ts
```

### 2.2 Configuración de FastAPI para Schema Completo

```python
# app/main.py

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="AI-Native Platform API",
    version="1.0.0",
    description="Plataforma educativa AI-Native para UTN FRM",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=[
            {"name": "auth", "description": "Autenticación y autorización"},
            {"name": "courses", "description": "Cursos, comisiones e inscripciones"},
            {"name": "exercises", "description": "Ejercicios, submissions y sandbox"},
            {"name": "tutor", "description": "Tutor IA socrático y streaming WS"},
            {"name": "cognitive", "description": "Clasificación cognitiva y CTR"},
            {"name": "governance", "description": "Gobernanza, prompts y analytics"},
        ],
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

---

## 3. Reglas de Propiedad de Schemas

Cada tabla en PostgreSQL pertenece a exactamente un módulo. Solo ese módulo puede realizar escrituras. Los demás módulos solo pueden leer mediante endpoints REST del módulo propietario.

### 3.1 Tabla de Propiedad

| Schema PostgreSQL | Módulo propietario (escribe)               | Lectura por otros módulos |
|-------------------|--------------------------------------------|---------------------------|
| `operational`     | features/auth, courses, exercises, sandbox, tutor (Fases 0-2) | features/cognitive (via REST) |
| `cognitive`       | features/cognitive, evaluation (Fase 3 únicamente) | features/governance (via REST) |
| `governance`      | features/governance (Fase 3)               | features/tutor (lee prompt activo via REST) |
| `analytics`       | features/evaluation, governance (Fase 3)   | Docentes via API endpoints |

### 3.2 Enforcement en Código

```python
# app/shared/enforcement.py

# Convención: cada repositorio declara su schema propietario
# Un linter personalizado (pre-commit hook) verifica que ningún
# repositorio acceda a tablas de otro schema.

class BaseRepository:
    OWNED_SCHEMA: str  # Debe ser declarado por cada subclase

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'OWNED_SCHEMA') or not cls.OWNED_SCHEMA:
            raise TypeError(
                f"{cls.__name__} debe declarar OWNED_SCHEMA. "
                "Solo puedes acceder a tablas de tu schema propietario."
            )
```

---

## 4. Response Wrapper Estándar

Todos los endpoints REST de la plataforma retornan un envelope consistente que facilita el manejo uniforme en el frontend y en los clientes externos.

### 4.1 Estructura del Wrapper

```python
# app/shared/schemas/response.py

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str = Field(description="Código de error legible por máquina")
    message: str = Field(description="Descripción en lenguaje natural")
    field: str | None = Field(
        default=None,
        description="Campo que causó el error (para errores de validación)"
    )


class ApiResponse(BaseModel, Generic[T]):
    """
    Envelope estándar para todas las respuestas REST.

    Ejemplo exitoso:
        { "status": "ok", "data": {...}, "meta": null, "errors": [] }

    Ejemplo de error:
        { "status": "error", "data": null, "meta": null,
          "errors": [{"code": "NOT_FOUND", "message": "..."}] }
    """

    status: str = Field(
        description="'ok' o 'error'",
        examples=["ok", "error"],
    )
    data: T | None = Field(
        default=None,
        description="Payload de la respuesta. Null en caso de error.",
    )
    meta: PaginationMeta | dict[str, Any] | None = Field(
        default=None,
        description="Metadata: paginación, tiempos de procesamiento, etc.",
    )
    errors: list[ErrorDetail] = Field(
        default_factory=list,
        description="Lista de errores. Vacía en caso de éxito.",
    )


def success(data: Any, meta: Any = None) -> ApiResponse:
    return ApiResponse(status="ok", data=data, meta=meta, errors=[])


def error(
    code: str,
    message: str,
    field: str | None = None,
    extra_errors: list[ErrorDetail] | None = None,
) -> ApiResponse:
    errors = [ErrorDetail(code=code, message=message, field=field)]
    if extra_errors:
        errors.extend(extra_errors)
    return ApiResponse(status="error", data=None, meta=None, errors=errors)
```

### 4.2 Uso en un Endpoint

```python
# app/features/exercises/router.py

from fastapi import APIRouter, HTTPException
from app.shared.schemas.responses import ApiResponse, success, error
from app.features.exercises.schemas import ExerciseResponse, ExerciseCreateRequest
from app.features.exercises.service import ExerciseService

router = APIRouter(prefix="/api/v1", tags=["exercises"])

@router.get(
    "/exercises/{exercise_id}",
    response_model=ApiResponse[ExerciseResponse],
)
async def get_exercise(
    exercise_id: str,
    service: ExerciseService = Depends(),
):
    try:
        exercise = await service.get_by_id(exercise_id)
        return success(data=exercise)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=error("NOT_FOUND", str(e)).model_dump(),
        )
```

### 4.3 Tipos TypeScript del Wrapper

```typescript
// src/types/api-response.ts (auto-generado + manual para generics)

export interface ApiResponse<T> {
  status: "ok" | "error";
  data: T | null;
  meta: PaginationMeta | Record<string, unknown> | null;
  errors: ErrorDetail[];
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
  field: string | null;
}

// Helper de tipo para extraer data
export type ApiData<T> = T extends ApiResponse<infer D> ? D : never;
```

---

## 5. Pydantic Schemas como DTOs de Contrato

Los schemas Pydantic son el contrato entre la capa HTTP y la capa de servicios. Definen exactamente qué datos acepta y retorna cada endpoint.

### 5.1 Convenciones de Nomenclatura

| Sufijo | Propósito |
|--------|-----------|
| `CreateRequest` | Body para POST (creación) |
| `UpdateRequest` | Body para PUT/PATCH (actualización) |
| `Response` | Payload que retorna la API |
| `ListResponse` | Payload de lista (con paginación) |
| `FilterParams` | Query params para filtrado |
| `Summary` | Versión reducida de Response (para listas) |

### 5.2 Ejemplo: Schema de Ejercicio

```python
# app/features/exercises/schemas.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal


class TestCaseSchema(BaseModel):
    id: str
    input: str
    expected_output: str
    is_hidden: bool = False
    description: str | None = None


class ExerciseCreateRequest(BaseModel):
    """DTO para crear un ejercicio. Usado en POST /phase1/exercises."""

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    language: Literal["python", "javascript"] = "python"
    starter_code: str = Field(default="", max_length=10000)
    test_cases: list[TestCaseSchema] = Field(min_length=1, max_length=20)
    max_attempts: int = Field(default=10, ge=1, le=100)
    time_limit_minutes: int = Field(default=60, ge=5, le=480)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("test_cases")
    @classmethod
    def at_least_one_visible_test(cls, v: list[TestCaseSchema]):
        visible = [tc for tc in v if not tc.is_hidden]
        if not visible:
            raise ValueError("Debe haber al menos un test case visible para el estudiante")
        return v


class ExerciseResponse(BaseModel):
    """DTO de respuesta para un ejercicio."""

    id: str
    title: str
    description: str
    difficulty: str
    language: str
    starter_code: str
    test_cases: list[TestCaseSchema]
    max_attempts: int
    time_limit_minutes: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    created_by_id: str

    model_config = {"from_attributes": True}


class ExerciseSummary(BaseModel):
    """Versión reducida para listas. No incluye test cases ni código."""

    id: str
    title: str
    difficulty: str
    language: str
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 5.3 Schema de Submission

```python
# app/features/exercises/schemas_submission.py

from pydantic import BaseModel, Field
from datetime import datetime


class SubmissionCreateRequest(BaseModel):
    exercise_id: str
    code: str = Field(min_length=1, max_length=50000)
    language: str = "python"


class TestResultSchema(BaseModel):
    test_id: str
    passed: bool
    expected: str
    actual: str
    execution_time_ms: int


class SubmissionResponse(BaseModel):
    id: str
    exercise_id: str
    student_id: str
    code: str
    status: str   # "pending" | "running" | "passed" | "failed" | "error"
    score: float | None  # NUMERIC(5,2) → 0.00 a 100.00
    test_results: list[TestResultSchema]
    stdout: str
    stderr: str
    execution_time_ms: int | None
    attempt_number: int
    submitted_at: datetime
    graded_at: datetime | None

    model_config = {"from_attributes": True}
```

---

## 6. Tipos TypeScript Auto-generados desde OpenAPI

El frontend consume los tipos directamente del schema OpenAPI usando `openapi-typescript`.

### 6.1 Script de Generación

```bash
# scripts/generate-types.sh
#!/bin/bash
set -e

echo "Iniciando servidor en background para generación de tipos..."
cd backend && uvicorn app.main:app --port 8099 &
SERVER_PID=$!
sleep 3

echo "Generando tipos TypeScript desde OpenAPI..."
npx openapi-typescript http://localhost:8099/openapi.json \
  --output frontend/src/types/api.generated.ts \
  --prettier \
  --alphabetize

kill $SERVER_PID
echo "Tipos generados en frontend/src/types/api.generated.ts"
```

### 6.2 Uso de los Tipos Generados

```typescript
// src/api/exerciseApi.ts

import type { components, paths } from "@/types/api.generated";

// Alias de tipos desde el schema generado
type ExerciseResponse = components["schemas"]["ExerciseResponse"];
type ExerciseCreateRequest = components["schemas"]["ExerciseCreateRequest"];
type SubmissionResponse = components["schemas"]["SubmissionResponse"];

// Path types para verificar que los endpoints existen en el contrato
type GetExercisePath = paths["/api/v1/exercises/{exercise_id}"]["get"];
type GetExerciseResponse = GetExercisePath["responses"]["200"]["content"]["application/json"];

export const exerciseApi = {
  async getById(id: string): Promise<ExerciseResponse> {
    const res = await fetch(`/api/v1/exercises/${id}`);
    const body: GetExerciseResponse = await res.json();

    if (body.status !== "ok") {
      throw new ApiError(body.errors[0].code, body.errors[0].message);
    }

    return body.data!;
  },

  async create(data: ExerciseCreateRequest): Promise<ExerciseResponse> {
    const res = await fetch("/api/v1/exercises", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await res.json();

    if (!res.ok) throw new ApiError(body.errors[0].code, body.errors[0].message);
    return body.data;
  },
};
```

---

## 7. LLM Adapter Protocol

El tutor IA debe comportarse de forma idéntica independientemente del proveedor de LLM (Anthropic Claude, OpenAI GPT-4, Ollama local). Esta invarianza es un requisito de la tesis doctoral: los experimentos deben poder replicarse con diferentes modelos.

### 7.1 Protocolo (Interface)

```python
# app/shared/llm/protocol.py

from typing import AsyncIterator, Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str        # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMStreamChunk:
    text: str         # Fragmento de texto generado
    is_final: bool    # True en el último chunk
    usage: dict | None = None  # Tokens usados (solo en chunk final)


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict  # {"input_tokens": int, "output_tokens": int}


@runtime_checkable
class LLMAdapter(Protocol):
    """
    Protocolo que todos los adaptadores LLM deben implementar.

    La invarianza de comportamiento se verifica mediante conformity tests
    que corren contra todos los adaptadores registrados.
    """

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Completación no-streaming. Retorna la respuesta completa."""
        ...

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Streaming token a token. Retorna un async iterator de chunks."""
        ...

    def model_name(self) -> str:
        """Nombre del modelo activo (para logging y auditoría)."""
        ...
```

### 7.2 Adaptador Anthropic

```python
# app/shared/llm/adapters/anthropic_adapter.py

import anthropic
from typing import AsyncIterator
from app.shared.llm.protocol import LLMAdapter, LLMMessage, LLMResponse, LLMStreamChunk
from app.config import settings


class AnthropicAdapter:
    """Adaptador para Anthropic Claude via SDK oficial."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = model

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield LLMStreamChunk(text=text, is_final=False)

            # Chunk final con usage
            final = await stream.get_final_message()
            yield LLMStreamChunk(
                text="",
                is_final=True,
                usage={
                    "input_tokens": final.usage.input_tokens,
                    "output_tokens": final.usage.output_tokens,
                },
            )


# Verificar en tiempo de import que implementa el protocolo
assert isinstance(AnthropicAdapter(), LLMAdapter), \
    "AnthropicAdapter no implementa el protocolo LLMAdapter"
```

### 7.3 Adaptador OpenAI

```python
# app/shared/llm/adapters/openai_adapter.py

from openai import AsyncOpenAI
from typing import AsyncIterator
from app.shared.llm.protocol import LLMAdapter, LLMMessage, LLMResponse, LLMStreamChunk
from app.config import settings


class OpenAIAdapter:
    """Adaptador para OpenAI GPT via SDK oficial."""

    def __init__(self, model: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = model

    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(
            {"role": m.role, "content": m.content} for m in messages
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(
            {"role": m.role, "content": m.content} for m in messages
        )

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield LLMStreamChunk(
                    text=chunk.choices[0].delta.content,
                    is_final=False,
                )

        yield LLMStreamChunk(text="", is_final=True)
```

### 7.4 Tests de Conformidad

```python
# tests/shared/llm/test_adapter_conformity.py
"""
Tests de conformidad que corren contra TODOS los adaptadores.
Garantizan que el comportamiento es invariante ante cambios de proveedor.
"""

import pytest
from app.shared.llm.protocol import LLMAdapter, LLMMessage

ADAPTERS_TO_TEST = [
    pytest.param("anthropic", id="anthropic"),
    pytest.param("openai", id="openai"),
    pytest.param("ollama", id="ollama"),
]

@pytest.mark.parametrize("adapter_name", ADAPTERS_TO_TEST)
async def test_complete_returns_non_empty_response(adapter_name, get_adapter):
    adapter: LLMAdapter = get_adapter(adapter_name)
    messages = [LLMMessage(role="user", content="Di solo 'ok'")]
    response = await adapter.complete(messages, max_tokens=10)

    assert response.content, "La respuesta no debe ser vacía"
    assert response.model, "Debe retornar el nombre del modelo"
    assert "input_tokens" in response.usage
    assert "output_tokens" in response.usage


@pytest.mark.parametrize("adapter_name", ADAPTERS_TO_TEST)
async def test_stream_yields_chunks_and_final(adapter_name, get_adapter):
    adapter: LLMAdapter = get_adapter(adapter_name)
    messages = [LLMMessage(role="user", content="Cuenta del 1 al 3")]

    chunks = []
    async for chunk in adapter.stream(messages, max_tokens=50):
        chunks.append(chunk)

    assert chunks, "Debe haber al menos un chunk"
    assert chunks[-1].is_final, "El último chunk debe tener is_final=True"

    text_chunks = [c for c in chunks if not c.is_final]
    assert text_chunks, "Debe haber al menos un chunk de texto"
```

---

## 8. Repository Base Class

Todos los repositorios de la plataforma heredan de `BaseRepository`, que define el contrato CRUD y gestiona la sesión de base de datos.

```python
# app/shared/repositories/base.py

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.exceptions import NotFoundError

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT")
UpdateSchemaT = TypeVar("UpdateSchemaT")


class BaseRepository(ABC, Generic[ModelT]):
    """
    Repositorio base con operaciones CRUD estándar.

    Cada repositorio concreto:
    1. Declara OWNED_SCHEMA (qué schema de PostgreSQL posee).
    2. Declara el modelo SQLAlchemy que gestiona.
    3. Puede sobreescribir métodos o agregar queries específicos del dominio.
    """

    OWNED_SCHEMA: str  # Ej: "operational", "cognitive"
    model: type[ModelT]

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, id: str | UUID) -> ModelT:
        """Busca una entidad por ID. Lanza NotFoundError si no existe."""
        result = await self._db.get(self.model, str(id))
        if not result:
            raise NotFoundError(
                f"{self.model.__name__} con id={id} no encontrado"
            )
        return result

    async def get_by_id_or_none(self, id: str | UUID) -> ModelT | None:
        """Busca una entidad por ID. Retorna None si no existe."""
        return await self._db.get(self.model, str(id))

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        """
        Lista entidades con paginación.

        Returns:
            Tuple de (items, total_count).
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if value is not None:
                    query = query.where(
                        getattr(self.model, field) == value
                    )
                    count_query = count_query.where(
                        getattr(self.model, field) == value
                    )

        total = await self._db.scalar(count_query)
        result = await self._db.execute(
            query.offset(offset).limit(limit)
        )
        items = list(result.scalars().all())

        return items, total or 0

    async def create(self, data: dict[str, Any]) -> ModelT:
        """Crea una entidad con los datos provistos."""
        instance = self.model(**data)
        self._db.add(instance)
        await self._db.flush()
        await self._db.refresh(instance)
        return instance

    async def update(self, id: str | UUID, data: dict[str, Any]) -> ModelT:
        """Actualiza campos de una entidad. Lanza NotFoundError si no existe."""
        instance = await self.get_by_id(id)

        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        await self._db.flush()
        await self._db.refresh(instance)
        return instance

    async def soft_delete(self, id: str | UUID) -> None:
        """
        Soft delete: marca is_active = False.
        Solo disponible en repositorios de entidades con soft delete.
        Repos de tablas inmutables (cognitive_events, tutor_interactions, etc.)
        NO heredan este método — las tablas inmutables no tienen is_active.
        """
        stmt = (
            update(self.model)
            .where(getattr(self.model, "id") == str(id))
            .values(is_active=False)
        )
        await self._db.execute(stmt)
        await self._db.flush()

    async def exists(self, id: str | UUID) -> bool:
        """Verifica si una entidad existe sin cargarla completa."""
        result = await self._db.scalar(
            select(func.count())
            .select_from(self.model)
            .where(getattr(self.model, "id") == str(id))
        )
        return (result or 0) > 0


# Implementación concreta de ejemplo
class ExerciseRepository(BaseRepository):
    OWNED_SCHEMA = "operational"
    model = Exercise  # type: ignore

    async def get_by_difficulty(
        self, difficulty: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Exercise], int]:
        return await self.list(
            offset=offset,
            limit=limit,
            filters={"difficulty": difficulty},
        )

    async def count_submissions(self, exercise_id: str) -> int:
        result = await self._db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.exercise_id == exercise_id)
        )
        return result or 0
```

---

## 9. Unit of Work Abstraction

El Unit of Work (UoW) garantiza que un conjunto de operaciones de repositorio se ejecute dentro de una única transacción de base de datos. Si alguna falla, todas se revierten.

```python
# app/shared/uow.py

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.repositories.exercise_repo import ExerciseRepository
from app.shared.repositories.submission_repo import SubmissionRepository
from app.shared.repositories.tutor_repo import TutorInteractionRepository
from app.shared.repositories.cognitive_repo import CognitiveRepository
from app.shared.repositories.governance_repo import GovernanceRepository


class UnitOfWork:
    """
    Unit of Work que agrupa repositorios bajo una sola transacción.

    Uso:
        async with uow:
            exercise = await uow.exercises.get_by_id(exercise_id)
            submission = await uow.submissions.create({...})
            await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        self.submissions = SubmissionRepository(self._session)
        self.cognitive_events = CognitiveRepository(self._session)
        self.tutor_interactions = TutorInteractionRepository(self._session)
        self.governance_events = GovernanceRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()


@asynccontextmanager
async def get_uow(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[UnitOfWork, None]:
    """Context manager conveniente para inyección de dependencias."""
    async with UnitOfWork(session_factory) as uow:
        yield uow


# Uso en un servicio
class SubmissionService:
    def __init__(self, uow_factory):
        self._uow_factory = uow_factory

    async def submit_exercise(
        self,
        student_id: str,
        exercise_id: str,
        code: str,
    ) -> SubmissionResponse:
        async with get_uow(self._uow_factory) as uow:
            exercise = await uow.exercises.get_by_id(exercise_id)

            # Verificar intentos disponibles
            submission_count = await uow.submissions.count_by_student_exercise(
                student_id, exercise_id
            )
            if submission_count >= exercise.max_attempts:
                raise DomainError(
                    "MAX_ATTEMPTS_REACHED",
                    f"Se alcanzó el máximo de {exercise.max_attempts} intentos",
                )

            submission = await uow.submissions.create({
                "student_id": student_id,
                "exercise_id": exercise_id,
                "code": code,
                "status": "pending",
                "attempt_number": submission_count + 1,
            })

            await uow.commit()
            return SubmissionResponse.model_validate(submission)
```

---

## 10. Jerarquía de Excepciones de Dominio

Una jerarquía de excepciones clara permite manejar errores de negocio de forma uniforme en toda la aplicación y mapearlos a respuestas HTTP consistentes.

```python
# app/shared/exceptions.py

from typing import Any


class DomainError(Exception):
    """
    Excepción base para todos los errores de dominio de la plataforma.

    Todos los errores de negocio heredan de esta clase.
    Los errores técnicos (DB down, red, etc.) NO heredan — se propagan como excepciones estándar.
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ─── Errores de Acceso y Recursos ────────────────────────────────────────────

class NotFoundError(DomainError):
    """El recurso solicitado no existe en la base de datos."""

    def __init__(self, message: str, resource_type: str = "", resource_id: str = ""):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class AuthorizationError(DomainError):
    """El usuario no tiene permisos para realizar la acción solicitada."""

    def __init__(self, message: str = "No tenés permisos para esta acción"):
        super().__init__(code="FORBIDDEN", message=message)


class AuthenticationError(DomainError):
    """Credenciales inválidas o token expirado."""

    def __init__(self, message: str = "Autenticación requerida"):
        super().__init__(code="UNAUTHORIZED", message=message)


# ─── Errores de Validación ────────────────────────────────────────────────────

class ValidationError(DomainError):
    """Los datos provistos no pasan las reglas de negocio."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details={"field": field} if field else {},
        )


class ConflictError(DomainError):
    """La operación entra en conflicto con el estado actual del sistema."""

    def __init__(self, message: str):
        super().__init__(code="CONFLICT", message=message)


# ─── Errores de Límites y Cuotas ─────────────────────────────────────────────

class MaxAttemptsReachedError(DomainError):
    """El estudiante agotó los intentos disponibles para un ejercicio."""

    def __init__(self, exercise_id: str, max_attempts: int):
        super().__init__(
            code="MAX_ATTEMPTS_REACHED",
            message=f"Se alcanzó el límite de {max_attempts} intentos",
            details={"exercise_id": exercise_id, "max_attempts": max_attempts},
        )


class RateLimitError(DomainError):
    """Demasiadas solicitudes en un período de tiempo."""

    def __init__(self, retry_after_seconds: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Demasiadas solicitudes. Reintentar en {retry_after_seconds}s",
            details={"retry_after_seconds": retry_after_seconds},
        )


# ─── Errores de Ejecución de Código ──────────────────────────────────────────

class CodeExecutionTimeoutError(DomainError):
    """El código del estudiante excedió el tiempo límite de ejecución."""

    def __init__(self, timeout_seconds: int = 10):
        super().__init__(
            code="EXECUTION_TIMEOUT",
            message=f"El código tardó más de {timeout_seconds} segundos",
            details={"timeout_seconds": timeout_seconds},
        )


class CodeExecutionSecurityError(DomainError):
    """El código intentó realizar una operación no permitida en el sandbox."""

    def __init__(self, attempted_operation: str):
        super().__init__(
            code="SECURITY_VIOLATION",
            message="El código intentó realizar una operación no permitida",
            details={"attempted_operation": attempted_operation},
        )


# ─── Errores de Integridad del CTR ───────────────────────────────────────────

class CTRIntegrityError(DomainError):
    """La cadena de hash del CTR fue comprometida."""

    def __init__(self, session_id: str, expected_hash: str, actual_hash: str):
        super().__init__(
            code="CTR_INTEGRITY_VIOLATION",
            message="La integridad de la cadena CTR fue comprometida",
            details={
                "session_id": session_id,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
            },
        )


# ─── Handler Global en FastAPI ────────────────────────────────────────────────

from fastapi import Request
from fastapi.responses import JSONResponse

HTTP_STATUS_MAP = {
    "NOT_FOUND": 404,
    "FORBIDDEN": 403,
    "UNAUTHORIZED": 401,
    "VALIDATION_ERROR": 422,
    "CONFLICT": 409,
    "MAX_ATTEMPTS_REACHED": 422,
    "RATE_LIMIT_EXCEEDED": 429,
    "EXECUTION_TIMEOUT": 408,
    "SECURITY_VIOLATION": 403,
    "CTR_INTEGRITY_VIOLATION": 500,
}

async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = HTTP_STATUS_MAP.get(exc.code, 400)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "data": None,
            "meta": None,
            "errors": [{
                "code": exc.code,
                "message": exc.message,
                "field": exc.details.get("field"),
            }],
        },
    )

# Registrar en main.py:
# app.add_exception_handler(DomainError, domain_error_handler)
```

---

## 11. Contratos de Servicios entre Módulos

Cuando Phase 3 necesita datos de Phase 1 o Phase 2, los solicita via REST. Los servicios que exponen datos a otros módulos tienen contratos explícitos en el schema OpenAPI.

```python
# app/features/cognitive/clients/exercises_client.py
"""
Cliente HTTP interno para consumir la API de exercises.
features/cognitive NUNCA importa directamente de features/exercises.*
"""

import httpx
from app.config import settings
from app.features.cognitive.schemas import ExerciseSummary, SubmissionSummary


class ExercisesClient:
    """
    Cliente para la API REST de exercises.
    Desacopla cognitive de la implementación interna de exercises.
    """

    BASE_URL = f"http://localhost:{settings.APP_PORT}/api/v1"

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(5.0),
            headers={"X-Internal-Service": "phase3"},
        )

    async def get_exercise(self, exercise_id: str) -> ExerciseSummary:
        response = await self._client.get(f"/api/v1/exercises/{exercise_id}")
        response.raise_for_status()
        data = response.json()
        return ExerciseSummary(**data["data"])

    async def get_student_submissions(
        self,
        student_id: str,
        exercise_id: str,
    ) -> list[SubmissionSummary]:
        response = await self._client.get(
            f"/submissions",
            params={"student_id": student_id, "exercise_id": exercise_id},
        )
        response.raise_for_status()
        data = response.json()
        return [SubmissionSummary(**s) for s in data["data"]["items"]]
```

---

## 12. Invariantes y Reglas de Negocio

Las invariantes son reglas que el dominio debe respetar en todo momento. Se implementan en la capa de dominio, no en la de presentación.

```python
# app/features/exercises/domain/submission.py

from dataclasses import dataclass
from datetime import datetime
from app.shared.exceptions import MaxAttemptsReachedError, ValidationError


@dataclass
class Submission:
    """Entidad de dominio para una submission de ejercicio."""

    id: str
    student_id: str
    exercise_id: str
    code: str
    attempt_number: int
    max_attempts_allowed: int

    # Invariante: el código no puede estar vacío
    def __post_init__(self):
        if not self.code.strip():
            raise ValidationError("El código no puede estar vacío", field="code")

        if self.attempt_number > self.max_attempts_allowed:
            raise MaxAttemptsReachedError(
                exercise_id=self.exercise_id,
                max_attempts=self.max_attempts_allowed,
            )

    def can_submit(self) -> bool:
        """Verifica si el estudiante puede realizar otro intento."""
        return self.attempt_number < self.max_attempts_allowed

    @property
    def is_final_attempt(self) -> bool:
        return self.attempt_number == self.max_attempts_allowed
```

---

*Documento generado para el proyecto AI-Native — UTN FRM. Tesis doctoral sobre evaluación cognitiva asistida por IA en educación en programación.*
