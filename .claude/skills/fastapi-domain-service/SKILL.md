---
name: fastapi-domain-service
description: >
  Impone arquitectura de routers delgados que delegan en servicios de dominio con
  inyección por constructor, excepciones de dominio propias y schemas Pydantic v2
  con wrapper de respuesta estandarizado. Trigger: al trabajar en routers FastAPI,
  servicios, dependencias o schemas de la plataforma AI-Native.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o modificar un router FastAPI (`routers/`)
- Al implementar un servicio de dominio (`services/`)
- Al definir schemas de entrada/salida (`schemas/`)
- Al manejar errores de negocio que no son errores HTTP
- Al inyectar dependencias (repositorios, servicios, configuración)

## Patrones Críticos

### 1. Router delgado → servicio → respuesta

El router solo valida la entrada, llama al servicio y envuelve la respuesta.
Nunca contiene lógica de negocio.

```python
# routers/tutor.py
from fastapi import APIRouter, Depends, status
from app.schemas.tutor import AskQuestionRequest, QuestionResponse
from app.services.tutor_service import TutorService
from app.api.deps import get_tutor_service
from app.api.response import ApiResponse

router = APIRouter(prefix="/tutor", tags=["tutor"])

@router.post(
    "/ask",
    response_model=ApiResponse[QuestionResponse],
    status_code=status.HTTP_200_OK,
)
async def ask_question(
    body: AskQuestionRequest,
    service: TutorService = Depends(get_tutor_service),
) -> ApiResponse[QuestionResponse]:
    result = await service.ask(body)
    return ApiResponse.ok(result)
```

### 2. Servicio de dominio con inyección de repositorio

El servicio recibe sus dependencias por constructor. Nunca importa `AsyncSession`
directamente; trabaja con repositorios definidos como protocolos.

```python
# services/tutor_service.py
from app.repositories.protocols import SessionRepositoryProtocol
from app.repositories.protocols import EvaluationRepositoryProtocol
from app.schemas.tutor import AskQuestionRequest, QuestionResponse
from app.domain.exceptions import SessionNotFoundError, QuotaExceededError

class TutorService:
    def __init__(
        self,
        session_repo: SessionRepositoryProtocol,
        eval_repo: EvaluationRepositoryProtocol,
    ) -> None:
        self._session_repo = session_repo
        self._eval_repo = eval_repo

    async def ask(self, request: AskQuestionRequest) -> QuestionResponse:
        session = await self._session_repo.get_active(request.student_id)
        if session is None:
            raise SessionNotFoundError(request.student_id)
        if session.quota_exhausted:
            raise QuotaExceededError(session.id)
        # lógica socrática aquí
        ...
```

### 3. Jerarquía de excepciones de dominio + handler global

Las excepciones de dominio no conocen HTTP. El handler las traduce en el límite
de la capa de presentación.

```python
# domain/exceptions.py
class DomainError(Exception):
    """Base para todos los errores de dominio."""
    pass

class SessionNotFoundError(DomainError):
    def __init__(self, student_id: str) -> None:
        super().__init__(f"Sesión activa no encontrada para alumno {student_id!r}")
        self.student_id = student_id

class QuotaExceededError(DomainError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Cuota agotada en sesión {session_id!r}")
        self.session_id = session_id

# api/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from app.domain.exceptions import SessionNotFoundError, QuotaExceededError

async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    mapping = {
        SessionNotFoundError: (404, "SESSION_NOT_FOUND"),
        QuotaExceededError: (429, "QUOTA_EXCEEDED"),
    }
    status_code, code = mapping.get(type(exc), (400, "DOMAIN_ERROR"))
    return JSONResponse(
        status_code=status_code,
        content={"ok": False, "error": {"code": code, "detail": str(exc)}},
    )
```

### 4. Convenciones de schemas Pydantic v2

`CreateXRequest` para creación, `XResponse` para salida, `XBase` para campos
compartidos. Siempre `model_config = ConfigDict(from_attributes=True)` en
responses que se mapean desde ORM.

```python
# schemas/tutor.py
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class AskQuestionBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class AskQuestionRequest(AskQuestionBase):
    student_id: UUID
    session_id: UUID | None = None

class QuestionResponse(AskQuestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    socratic_hint: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
```

## Anti-patrones

### Lógica de negocio en el router

```python
# NO — el router decide reglas de negocio
@router.post("/ask")
async def ask(body: AskQuestionRequest, db: AsyncSession = Depends(get_db)):
    session = await db.get(Session, body.session_id)
    if session.quota_exhausted:          # lógica de dominio aquí ← MAL
        raise HTTPException(status_code=429, detail="Quota exceeded")
    ...

# SI — delegar siempre al servicio
@router.post("/ask")
async def ask(body: AskQuestionRequest, svc: TutorService = Depends(get_tutor_service)):
    result = await svc.ask(body)
    return ApiResponse.ok(result)
```

### Servicio importando AsyncSession directamente

```python
# NO — acopla el servicio a SQLAlchemy
class TutorService:
    def __init__(self, db: AsyncSession): ...

# SI — usar protocolo/repositorio como abstracción
class TutorService:
    def __init__(self, session_repo: SessionRepositoryProtocol): ...
```

### Levantar HTTPException desde la capa de servicio

```python
# NO — el servicio conoce detalles HTTP
async def ask(self, request): ...
    raise HTTPException(status_code=404, detail="Not found")  # ← MAL

# SI — excepción de dominio pura, HTTP solo en el handler
async def ask(self, request): ...
    raise SessionNotFoundError(request.student_id)
```

## Checklist

- [ ] El router no contiene `if`/`for` de lógica de negocio
- [ ] El servicio no importa `AsyncSession`, `HTTPException` ni `status`
- [ ] Toda excepción de negocio hereda de `DomainError`
- [ ] El handler global está registrado en `app.add_exception_handler`
- [ ] Schemas de request usan `CreateXRequest` o `XRequest`
- [ ] Schemas de response tienen `ConfigDict(from_attributes=True)` si vienen del ORM
- [ ] Las dependencias se resuelven en `api/deps.py`, no en el router
- [ ] `ApiResponse[T]` es el envelope de todas las respuestas exitosas
