# Patrones de Diseño — Plataforma AI-Native

**Versión**: 1.0  
**Fecha**: 2026-04-10  
**Stack**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async  

---

## Tabla de Contenidos

1. [Repository Pattern](#1-repository-pattern)
2. [Unit of Work](#2-unit-of-work)
3. [Domain Service](#3-domain-service)
4. [Event Bus](#4-event-bus)
5. [Hash Chain](#5-hash-chain)
6. [Dependency Injection](#6-dependency-injection)
7. [Strategy Pattern — LLM Adapters](#7-strategy-pattern--llm-adapters)
8. [Guard / Policy Pattern](#8-guard--policy-pattern)

---

## 1. Repository Pattern

### Qué es

El Repository Pattern abstrae el acceso a datos detrás de una interfaz de dominio. El Service no sabe si los datos vienen de PostgreSQL, un archivo, o un mock. Solo sabe que puede pedirlos al repositorio.

### Por qué se usa en este proyecto

1. **Testabilidad**: Los Services se testean con un `FakeRepository` en memoria sin necesidad de DB.
2. **Queries complejas encapsuladas**: El join entre `submissions` y `exercises` con filtros de comisión vive en el repositorio, no en el service.
3. **Cambio de ORM aislado**: Si migramos a asyncpg raw, solo cambia el repositorio.
4. **Carga de relaciones controlada**: El `selectinload` se define una vez en el repositorio, no se repite en cada service.

### Implementación

#### Base Repository (CRUD genérico)

```python
# backend/app/shared/repositories/base.py
from typing import Generic, TypeVar, Type, Sequence
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """
    Repositorio base con operaciones CRUD genéricas.
    Las subclases lo extienden con queries específicas de dominio.
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_by_id(self, id: UUID) -> ModelType | None:
        """Solo retorna entidades no eliminadas (soft delete)."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.is_active.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        page: int = 1,
        per_page: int = 20,
        only_active: bool = True
    ) -> tuple[Sequence[ModelType], int]:
        """Retorna (items, total_count) para paginación."""
        stmt = select(self.model)
        if only_active and hasattr(self.model, "is_active"):
            stmt = stmt.where(self.model.is_active.is_(True))
        
        # Count query
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt)
        
        # Paginated query
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total or 0
    
    async def save(self, entity: ModelType) -> ModelType:
        """Agrega o actualiza una entidad. No commitea — eso es rol del UoW."""
        self.session.add(entity)
        await self.session.flush()  # Para obtener el ID generado
        await self.session.refresh(entity)
        return entity
    
    async def soft_delete(self, id: UUID) -> bool:
        """Soft delete: marca is_active = False."""
        stmt = update(self.model).where(
            self.model.id == id
        ).values(is_active=False)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
```

#### Repository Específico con Queries de Dominio

```python
# backend/app/shared/repositories/submission_repo.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.shared.models.operational import Submission, Exercise, User

class SubmissionRepository(BaseRepository[Submission]):
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Submission)
    
    async def get_with_exercise(self, submission_id: UUID) -> Submission | None:
        """Carga la submission con su exercise y student en un solo query."""
        stmt = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(
                selectinload(Submission.exercise),
                selectinload(Submission.student)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_latest_by_student_exercise(
        self,
        student_id: UUID,
        exercise_id: UUID
    ) -> Submission | None:
        """Última entrega de un estudiante para un ejercicio."""
        stmt = (
            select(Submission)
            .where(
                Submission.student_id == student_id,
                Submission.exercise_id == exercise_id
            )
            .order_by(Submission.submitted_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_exercise_with_students(
        self,
        exercise_id: UUID,
        commission_id: UUID
    ) -> list[Submission]:
        """
        Lista todas las entregas de un ejercicio para una comisión.
        Hace join con enrollments para filtrar solo estudiantes inscriptos.
        """
        from app.shared.models.operational import Enrollment
        
        stmt = (
            select(Submission)
            .join(
                Enrollment,
                Enrollment.student_id == Submission.student_id
            )
            .where(
                Submission.exercise_id == exercise_id,
                Enrollment.commission_id == commission_id,
                Enrollment.is_active.is_(True)
            )
            .options(selectinload(Submission.student))
            .order_by(Submission.submitted_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Anti-patrón a Evitar

```python
# MAL: El Service hace queries directamente — viola la separación de capas
class SubmissionService:
    async def get_latest_submission(self, student_id: UUID, exercise_id: UUID):
        # NUNCA hacer esto en un service
        stmt = select(Submission).where(
            Submission.student_id == student_id,
            Submission.exercise_id == exercise_id
        ).order_by(Submission.submitted_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

# BIEN: El Service delega al repositorio
class SubmissionService:
    async def get_latest_submission(self, student_id: UUID, exercise_id: UUID):
        return await self.submission_repo.get_latest_by_student_exercise(
            student_id, exercise_id
        )
```

---

## 2. Unit of Work

### Qué es

El Unit of Work gestiona las transacciones de base de datos como una unidad lógica. Garantiza que múltiples operaciones de repositorio sean atómicas: o todas se commitean, o ninguna.

### Por qué se usa en este proyecto

1. **Transaccionalidad garantizada**: Crear una submission + registrar el evento cognitivo + emitir el evento de bus son atómicos.
2. **Sin commits accidentales**: Los repositories nunca commitean por sí mismos. Solo flushean. El commit está centralizado en el UoW.
3. **Rollback automático**: Si cualquier operación falla dentro del `async with`, el UoW hace rollback.
4. **Testing**: Se puede usar un UoW de test que siempre hace rollback.

### Implementación

```python
# backend/app/shared/db/unit_of_work.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.shared.repositories.submission_repo import SubmissionRepository
from app.shared.repositories.cognitive_repo import CognitiveRepository
from app.shared.repositories.governance_repo import GovernanceRepository


class UnitOfWork:
    """
    Gestiona la sesión de DB y los repositorios como una unidad transaccional.
    
    Uso:
        async with UnitOfWork(session_factory) as uow:
            submission = await uow.submissions.save(new_submission)
            await uow.cognitive.save_event(event)
            await uow.commit()  # Commit explícito
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
    
    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self._init_repositories()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        await self.session.close()
    
    def _init_repositories(self):
        """Inicializa todos los repositorios con la sesión actual."""
        self.submissions = SubmissionRepository(self.session)
        self.cognitive_events = CognitiveRepository(self.session)
        self.tutor_interactions = TutorInteractionRepository(self.session)
        self.governance_events = GovernanceRepository(self.session)
        # Agregar más repos según se necesiten
    
    async def commit(self) -> None:
        """Commitea la transacción. Solo llamar cuando todo fue correcto."""
        await self.session.commit()
    
    async def rollback(self) -> None:
        """Rollback explícito o llamado automáticamente en excepciones."""
        await self.session.rollback()
    
    async def flush(self) -> None:
        """Flush sin commit — útil para obtener IDs antes del commit."""
        await self.session.flush()


# Factory para inyección de dependencias
@asynccontextmanager
async def get_uow(session_factory: async_sessionmaker[AsyncSession]):
    async with UnitOfWork(session_factory) as uow:
        yield uow
```

### Uso en un Service

```python
# backend/app/features/exercises/service.py
class SubmissionService:
    
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory
    
    async def submit_exercise(
        self,
        student_id: UUID,
        exercise_id: UUID,
        code: str
    ) -> SubmissionDTO:
        async with self.uow_factory() as uow:
            # Verificar que el estudiante está inscripto
            enrollment = await uow.submissions.get_enrollment(
                student_id, exercise_id
            )
            if not enrollment:
                raise NotEnrolledException(student_id, exercise_id)
            
            # Crear la submission
            submission = Submission(
                student_id=student_id,
                exercise_id=exercise_id,
                code=code,
                status="pending"
            )
            saved = await uow.submissions.save(submission)
            
            # Registrar evento cognitivo
            await uow.cognitive.save_event(
                session_id=...,
                event_type="submission.created",
                payload={"submission_id": str(saved.id)}
            )
            
            # Commit atómico: ambas ops o ninguna
            await uow.commit()
            
            return SubmissionDTO.from_orm(saved)
```

### Anti-patrón a Evitar

```python
# MAL: Commits en los repositorios — no hay transaccionalidad entre repos
class SubmissionRepository:
    async def save(self, submission: Submission) -> Submission:
        self.session.add(submission)
        await self.session.commit()  # NUNCA — si falla el siguiente step, los datos quedan inconsistentes
        return submission

# MAL: Commit en el router
@router.post("/submit")
async def submit(data: SubmitRequest, session: AsyncSession = Depends(get_db)):
    submission = Submission(...)
    session.add(submission)
    await session.commit()  # NUNCA en el router — mezcla capas
```

---

## 3. Domain Service

### Qué es

El Domain Service contiene la lógica de negocio de un dominio. Es delgado respecto al Router (no sabe de HTTP) y delgado respecto al Repository (no sabe de SQL). Su trabajo es orquestar operaciones de dominio.

### Por qué se usa en este proyecto

1. **Separación de concerns**: El router valida la request, el service ejecuta la lógica, el repo persiste.
2. **Reusabilidad**: El mismo service puede ser llamado desde un HTTP endpoint, un WebSocket handler, o un job background.
3. **Testabilidad**: Los services se testean con mocks de repositorios sin levantar FastAPI.
4. **Excepciones de dominio**: El service lanza `DomainError`, el router las convierte en HTTP.

### Implementación

#### Excepciones de Dominio

```python
# backend/app/core/exceptions.py
from uuid import UUID

class DomainError(Exception):
    """Excepción base del dominio. NO es una HTTPException."""
    
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code

class NotFoundException(DomainError):
    def __init__(self, resource: str, id: UUID):
        super().__init__(
            message=f"El recurso '{resource}' con id '{id}' no existe.",
            code=f"{resource.upper()}_NOT_FOUND"
        )

class NotEnrolledException(DomainError):
    def __init__(self, student_id: UUID, exercise_id: UUID):
        super().__init__(
            message=f"El estudiante '{student_id}' no está inscripto en el curso del ejercicio '{exercise_id}'.",
            code="NOT_ENROLLED"
        )

class SessionAlreadyOpenException(DomainError):
    def __init__(self, student_id: UUID, exercise_id: UUID):
        super().__init__(
            message=f"Ya existe una sesión abierta para el estudiante '{student_id}' en el ejercicio '{exercise_id}'.",
            code="SESSION_ALREADY_OPEN"
        )
```

#### Service con Lógica de Dominio

```python
# backend/app/features/cognitive/service.py
from uuid import UUID
from app.core.exceptions import NotFoundException, SessionAlreadyOpenException
from app.features.cognitive.hash_chain import HashChainService
from app.shared.db.unit_of_work import UnitOfWork


class CognitiveService:
    """
    Service de dominio para la gestión del CTR (Registro de Traza Cognitiva).
    
    Solo conoce conceptos de dominio: sesiones, eventos, hashes.
    No conoce FastAPI, HTTP, ni SQL.
    """
    
    def __init__(self, uow: UnitOfWork, hash_chain: HashChainService):
        self.uow = uow
        self.hash_chain = hash_chain
    
    async def start_session(
        self,
        student_id: UUID,
        exercise_id: UUID
    ) -> CognitiveSessionDTO:
        """
        Inicia una sesión cognitiva.
        Lanza SessionAlreadyOpenException si ya hay una sesión abierta.
        """
        # Verificar que no hay sesión abierta
        existing = await self.uow.cognitive.get_open_session(
            student_id, exercise_id
        )
        if existing:
            raise SessionAlreadyOpenException(student_id, exercise_id)
        
        # Generar genesis hash
        from datetime import datetime, timezone
        started_at = datetime.now(timezone.utc)
        session_id = uuid4()
        genesis_hash = self.hash_chain.compute_genesis_hash(session_id, started_at)
        
        session = CognitiveSession(
            id=session_id,
            student_id=student_id,
            exercise_id=exercise_id,
            started_at=started_at,
            genesis_hash=genesis_hash,
            status="open"
        )
        
        saved = await self.uow.cognitive.save_session(session)
        await self.uow.commit()
        
        return CognitiveSessionDTO(
            session_id=saved.id,
            exercise_id=exercise_id,
            genesis_hash=genesis_hash,
            started_at=started_at,
            status="open"
        )
    
    async def record_event(
        self,
        session_id: UUID,
        event_type: str,
        payload: dict
    ) -> CognitiveEventDTO:
        """
        Registra un evento en la cadena CTR.
        Lanza NotFoundException si la sesión no existe.
        Lanza DomainError si la sesión está cerrada.
        """
        session = await self.uow.cognitive.get_session(session_id)
        if not session:
            raise NotFoundException("cognitive_session", session_id)
        
        if session.status != "open":
            from app.core.exceptions import DomainError
            raise DomainError(
                message="No se pueden registrar eventos en una sesión cerrada.",
                code="SESSION_CLOSED"
            )
        
        # Obtener el último hash de la cadena
        last_hash = await self.uow.cognitive.get_last_event_hash(session_id)
        if last_hash is None:
            last_hash = session.genesis_hash
        
        # Calcular el nuevo hash
        from datetime import datetime, timezone
        created_at = datetime.now(timezone.utc)
        sequence = await self.uow.cognitive.get_next_sequence(session_id)
        new_hash = self.hash_chain.compute_event_hash(
            last_hash, event_type, payload, created_at
        )
        
        event = CognitiveEvent(
            session_id=session_id,
            event_type=event_type,
            sequence_number=sequence,
            payload=payload,
            previous_hash=last_hash,
            event_hash=new_hash,
            created_at=created_at
        )
        
        saved = await self.uow.cognitive.save_event(event)
        await self.uow.commit()
        
        return CognitiveEventDTO(
            event_id=saved.id,
            sequence_number=sequence,
            event_hash=new_hash,
            created_at=created_at
        )
```

#### Router que Transforma Excepciones de Dominio

```python
# backend/app/features/cognitive/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.exceptions import DomainError, NotFoundException, SessionAlreadyOpenException

router = APIRouter()

@router.post("/cognitive/sessions/start", status_code=201)
async def start_cognitive_session(
    body: StartSessionRequest,
    current_user: User = Depends(get_current_student),
    service: CognitiveService = Depends(get_cognitive_service)
):
    try:
        session_dto = await service.start_session(
            student_id=current_user.id,
            exercise_id=body.exercise_id
        )
        return StandardResponse.ok(session_dto)
    
    except SessionAlreadyOpenException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message}
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message}
        )
    except DomainError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message}
        )
```

### Anti-patrón a Evitar

```python
# MAL: Lógica de negocio en el router
@router.post("/cognitive/sessions/start")
async def start_session(body: StartSessionRequest, session: AsyncSession = Depends(get_db)):
    # NUNCA poner lógica acá
    existing = await session.execute(
        select(CognitiveSession).where(
            CognitiveSession.student_id == current_user.id,
            CognitiveSession.status == "open"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Ya hay sesión abierta")
    # ...

# MAL: HTTPException en el service
class CognitiveService:
    async def start_session(self, ...):
        from fastapi import HTTPException  # NUNCA importar FastAPI en un service
        raise HTTPException(409, "Ya hay sesión abierta")
```

---

## 4. Event Bus

### Qué es

El Event Bus es un canal de comunicación asíncrono entre dominios. Permite que un dominio emita un evento sin saber quién lo escucha. Los suscriptores reaccionan cuando les interesa.

### Por qué se usa en este proyecto

1. **Desacoplamiento**: El dominio `exercises` no sabe que `cognitive` necesita registrar un evento cuando se crea una submission.
2. **Extensibilidad**: Se puede agregar un nuevo consumidor (ej: analytics) sin modificar el emisor.
3. **Resiliencia**: Si el consumidor falla, el evento puede reintentarse desde Redis.

### Implementación con Redis Streams

```python
# backend/app/core/event_bus.py
import json
from dataclasses import dataclass, asdict
from typing import Protocol, Callable, Awaitable
from uuid import UUID
from datetime import datetime
import redis.asyncio as redis


@dataclass
class DomainEvent:
    """Base para todos los eventos de dominio."""
    event_type: str
    correlation_id: UUID
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {k: str(v) if isinstance(v, (UUID, datetime)) else v 
                for k, v in asdict(self).items()}


@dataclass
class SubmissionCreatedEvent(DomainEvent):
    submission_id: UUID = field(default_factory=uuid4)
    student_id: UUID = field(default_factory=uuid4)
    exercise_id: UUID = field(default_factory=uuid4)
    code: str = ""
    event_type: str = "submission.created"


@dataclass
class TutorInteractionCompletedEvent(DomainEvent):
    interaction_id: UUID = field(default_factory=uuid4)
    student_id: UUID = field(default_factory=uuid4)
    exercise_id: UUID = field(default_factory=uuid4)
    n4_level: int | None = None
    event_type: str = "tutor.interaction_completed"


class EventBus:
    """
    Event Bus basado en Redis Streams.
    Los streams actúan como canales con persistencia y consumer groups.
    """
    
    STREAM_SUBMISSIONS = "events:submissions"
    STREAM_TUTOR = "events:tutor"
    STREAM_COGNITIVE = "events:cognitive"
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._handlers: dict[str, list[Callable]] = {}
    
    async def publish(self, event: DomainEvent, stream: str) -> str:
        """Publica un evento en un Redis Stream. Retorna el message ID."""
        message = event.to_dict()
        message_id = await self.redis.xadd(stream, message)
        return message_id.decode()
    
    async def publish_submission_created(self, event: SubmissionCreatedEvent):
        await self.publish(event, self.STREAM_SUBMISSIONS)
    
    async def publish_tutor_interaction(self, event: TutorInteractionCompletedEvent):
        await self.publish(event, self.STREAM_TUTOR)


class EventConsumer:
    """
    Consumer de eventos que corre en background.
    Usa consumer groups de Redis para garantizar at-least-once delivery.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        stream: str,
        group: str,
        consumer_name: str,
        handler: Callable[[dict], Awaitable[None]]
    ):
        self.redis = redis_client
        self.stream = stream
        self.group = group
        self.consumer_name = consumer_name
        self.handler = handler
    
    async def start(self):
        """Inicia el loop de consumo."""
        # Crear el consumer group si no existe
        try:
            await self.redis.xgroup_create(
                self.stream, self.group, id="0", mkstream=True
            )
        except Exception:
            pass  # El grupo ya existe
        
        while True:
            messages = await self.redis.xreadgroup(
                groupname=self.group,
                consumername=self.consumer_name,
                streams={self.stream: ">"},
                count=10,
                block=1000  # 1 segundo de timeout
            )
            
            for stream, msgs in (messages or []):
                for msg_id, data in msgs:
                    try:
                        await self.handler(data)
                        # ACK solo si el handler tuvo éxito
                        await self.redis.xack(self.stream, self.group, msg_id)
                    except Exception as e:
                        # El mensaje queda sin ACK → se reintentará
                        import logging
                        logging.error(f"Error procesando evento {msg_id}: {e}")
```

#### Handler de Cognitive que consume eventos de Submissions

```python
# backend/app/features/cognitive/event_handlers.py
from app.core.event_bus import EventConsumer
from app.features.cognitive.service import CognitiveService

async def handle_submission_created(data: dict):
    """
    Cuando se crea una submission, registrar el evento cognitivo correspondiente.
    """
    submission_id = UUID(data[b"submission_id"].decode())
    student_id = UUID(data[b"student_id"].decode())
    exercise_id = UUID(data[b"exercise_id"].decode())
    
    async with get_cognitive_uow() as uow:
        service = CognitiveService(uow)
        
        # Buscar sesión abierta del estudiante para este ejercicio
        open_session = await uow.cognitive.get_open_session(student_id, exercise_id)
        if open_session:
            await service.record_event(
                session_id=open_session.id,
                event_type="submission.created",
                payload={"submission_id": str(submission_id)}
            )


# Registro de consumers en el lifespan de FastAPI
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: iniciar consumers en background
    consumer = EventConsumer(
        redis_client=get_redis(),
        stream=EventBus.STREAM_SUBMISSIONS,
        group="cognitive-group",
        consumer_name="cognitive-worker-1",
        handler=handle_submission_created
    )
    task = asyncio.create_task(consumer.start())
    
    yield
    
    # Shutdown: cancelar consumers
    task.cancel()
```

### Anti-patrón a Evitar

```python
# MAL: Llamadas directas entre servicios de dominios distintos
class SubmissionService:
    def __init__(self, cognitive_service: CognitiveService):  # NUNCA
        self.cognitive_service = cognitive_service
    
    async def submit(self, ...):
        submission = await self.submission_repo.save(...)
        # Llamada directa: acoplamiento fuerte entre dominios
        await self.cognitive_service.record_event(...)

# BIEN: El dominio emite un evento y no sabe quién escucha
class SubmissionService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def submit(self, ...):
        submission = await self.submission_repo.save(...)
        await self.event_bus.publish_submission_created(
            SubmissionCreatedEvent(submission_id=submission.id, ...)
        )
```

---

## 5. Hash Chain

### Qué es

La Hash Chain es una estructura donde cada elemento contiene el hash del elemento anterior. Cualquier alteración en un elemento medio invalida todos los hashes siguientes, haciendo la manipulación detectable.

### Por qué se usa en este proyecto

El CTR (Registro de Traza Cognitiva) debe ser **a prueba de manipulación**. Un docente, administrador, o incluso un DBA con acceso directo a la DB no debería poder modificar o eliminar eventos de la traza cognitiva de un estudiante sin que se detecte.

### Implementación

```python
# backend/app/features/cognitive/hash_chain.py
import hashlib
import json
from datetime import datetime
from uuid import UUID


class HashChainService:
    """
    Servicio para gestionar la cadena de hash SHA-256 del CTR.
    
    La cadena garantiza que:
    - No se puede insertar un evento entre dos eventos existentes
    - No se puede modificar el payload de un evento
    - No se puede eliminar un evento sin romper todos los hashes siguientes
    """
    
    HASH_ENCODING = "utf-8"
    
    @staticmethod
    def compute_genesis_hash(session_id: UUID, started_at: datetime) -> str:
        """
        Hash inicial de la cadena. No tiene "previous_hash".
        Incorpora session_id y timestamp para que sea único por sesión.
        """
        data = f"GENESIS:{session_id}:{started_at.isoformat()}"
        return hashlib.sha256(data.encode(HashChainService.HASH_ENCODING)).hexdigest()
    
    @staticmethod
    def compute_event_hash(
        previous_hash: str,
        event_type: str,
        payload: dict,
        created_at: datetime
    ) -> str:
        """
        Calcula el hash de un evento.
        
        hash(n) = SHA256(hash(n-1) + event_type + serialize(payload) + timestamp)
        
        La serialización del payload es determinista:
        - Claves ordenadas alfabéticamente
        - Sin espacios innecesarios
        - Valores anidados también ordenados
        """
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        data = f"{previous_hash}:{event_type}:{payload_str}:{created_at.isoformat()}"
        return hashlib.sha256(data.encode(HashChainService.HASH_ENCODING)).hexdigest()
    
    @staticmethod
    def verify_chain_integrity(
        genesis_hash: str,
        events: list[dict]
    ) -> tuple[bool, int | None]:
        """
        Verifica que la cadena no fue alterada.
        
        Args:
            genesis_hash: El hash inicial de la sesión
            events: Lista de eventos ordenados por sequence_number ASC
        
        Returns:
            (True, None) si la cadena es válida
            (False, sequence_number) del primer evento corrupto
        """
        if not events:
            return True, None
        
        expected_previous = genesis_hash
        
        for event in events:
            # El previous_hash del evento debe coincidir con lo esperado
            if event["previous_hash"] != expected_previous:
                return False, event["sequence_number"]
            
            # Recalcular el hash actual del evento
            recomputed = HashChainService.compute_event_hash(
                previous_hash=event["previous_hash"],
                event_type=event["event_type"],
                payload=event["payload"],
                created_at=event["created_at"]
            )
            
            # El hash almacenado debe coincidir con el recalculado
            if recomputed != event["event_hash"]:
                return False, event["sequence_number"]
            
            # El siguiente evento debe apuntar al hash actual
            expected_previous = event["event_hash"]
        
        return True, None
    
    @staticmethod
    def compute_session_close_hash(
        last_event_hash: str,
        session_id: UUID,
        closed_at: datetime,
        total_events: int
    ) -> str:
        """
        Hash final de la sesión al cerrarla.
        Incorpora el total de eventos para detectar eliminaciones.
        """
        data = f"CLOSE:{session_id}:{last_event_hash}:{closed_at.isoformat()}:{total_events}"
        return hashlib.sha256(data.encode(HashChainService.HASH_ENCODING)).hexdigest()
```

#### Ejemplo de Cadena Visualizada

```
Session ID: a1b2c3...
Genesis Hash: sha256("GENESIS:a1b2c3...:2026-04-10T12:00:00") = "aaa111..."

Evento 1: session.started
  previous_hash: "aaa111..."
  event_type: "session.started"
  payload: {}
  created_at: 2026-04-10T12:00:01
  event_hash: sha256("aaa111...:session.started:{}:2026-04-10T12:00:01") = "bbb222..."

Evento 2: tutor.question_asked
  previous_hash: "bbb222..."
  event_type: "tutor.question_asked"
  payload: {"question": "¿Cómo empiezo?"}
  created_at: 2026-04-10T12:02:30
  event_hash: sha256("bbb222...:tutor.question_asked:{...}:...") = "ccc333..."

Si alguien modifica el payload del Evento 1:
  El event_hash recalculado del Evento 1 será "xxx999..." ≠ "bbb222..."
  El previous_hash del Evento 2 ("bbb222...") ya no coincide con el hash del Evento 1
  → CHAIN INTEGRITY: COMPROMISED at sequence 1
```

### Anti-patrón a Evitar

```python
# MAL: Hash solo del payload, sin encadenar con el anterior
def compute_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()
# Con este enfoque, se puede insertar o eliminar eventos sin que se detecte
# porque cada hash es independiente

# BIEN: Hash encadenado — cada evento depende de todos los anteriores
def compute_event_hash(previous_hash: str, ...) -> str:
    data = f"{previous_hash}:..."  # El previous_hash hace la cadena
    return hashlib.sha256(data.encode()).hexdigest()
```

---

## 6. Dependency Injection

### Qué es

FastAPI usa el patrón de Inyección de Dependencias con `Depends()`. Las dependencias son funciones que retornan objetos (sesiones de DB, services, usuarios actuales) y FastAPI las resuelve automáticamente.

### Por qué se usa en este proyecto

1. **No hay singletons globales**: Cada request obtiene su propia instancia de AsyncSession.
2. **Testing sencillo**: Se pueden reemplazar dependencias en tests con `app.dependency_overrides`.
3. **Composición declarativa**: El router declara qué necesita, no cómo crearlo.
4. **Cycle detection**: FastAPI detecta dependencias circulares en el startup.

### Implementación

#### Dependencias Base

```python
# backend/app/dependencies.py
from functools import lru_cache
from typing import Annotated, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.db.session import async_session_factory
from app.core.security import decode_access_token
from app.shared.models.operational import User


# ── Sesión de DB ──────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia que provee una AsyncSession por request.
    La sesión se cierra automáticamente al final del request.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


# ── Autenticación JWT ─────────────────────────────────────────────────────────

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodifica el JWT y retorna el usuario autenticado.
    Lanza 401 si el token es inválido o el usuario no existe.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token inválido o expirado."}
        )
    
    from app.shared.repositories.user_repo import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_active_by_id(UUID(payload["sub"]))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "El usuario no existe."}
        )
    
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Guards de Rol ─────────────────────────────────────────────────────────────

def require_role(*roles: str):
    """
    Fábrica de dependencias de rol. Uso: Depends(require_role("teacher", "admin"))
    """
    async def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"Se requiere rol: {', '.join(roles)}."}
            )
        return user
    return _check_role

CurrentStudent = Annotated[User, Depends(require_role("student"))]
CurrentTeacher = Annotated[User, Depends(require_role("teacher", "admin"))]
CurrentAdmin = Annotated[User, Depends(require_role("admin"))]


# ── Service Factories ─────────────────────────────────────────────────────────

async def get_cognitive_service(db: DatabaseSession) -> CognitiveService:
    """Fábrica del CognitiveService con todas sus dependencias resueltas."""
    from app.shared.db.unit_of_work import UnitOfWork
    from app.features.cognitive.hash_chain import HashChainService
    from app.features.cognitive.service import CognitiveService
    
    uow = UnitOfWork(async_session_factory)
    hash_chain = HashChainService()
    return CognitiveService(uow=uow, hash_chain=hash_chain)

CognitiveSvc = Annotated[CognitiveService, Depends(get_cognitive_service)]
```

#### Uso en Routers

```python
# backend/app/features/cognitive/router.py
from fastapi import APIRouter
from app.dependencies import CurrentStudent, CognitiveSvc, CurrentTeacher

router = APIRouter(prefix="/api/v1", tags=["cognitive"])

@router.post("/cognitive/sessions/start", status_code=201)
async def start_session(
    body: StartSessionRequest,
    current_user: CurrentStudent,        # Inyectado por FastAPI
    service: CognitiveSvc               # Inyectado por FastAPI
):
    ...

@router.get("/teacher/students/{student_id}/profile")
async def get_student_profile(
    student_id: UUID,
    current_teacher: CurrentTeacher,     # Solo teachers
    service: CognitiveSvc
):
    ...
```

#### Override de Dependencias en Tests

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_db, get_current_user

@pytest.fixture
def test_client(test_db_session, mock_user):
    # Reemplazar la sesión de DB real con la de test
    app.dependency_overrides[get_db] = lambda: test_db_session
    # Reemplazar la autenticación con un mock
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()
```

### Anti-patrón a Evitar

```python
# MAL: Singleton global de sesión — no es thread-safe con async
_global_session = None

def get_db():
    global _global_session
    if not _global_session:
        _global_session = create_session()
    return _global_session  # NUNCA: multiple requests comparten la misma sesión

# MAL: Instanciar services directamente en el router
@router.post("/sessions/start")
async def start_session(body: StartSessionRequest):
    db = next(get_db())  # NUNCA: next() en un async generator
    service = CognitiveService(db)  # NUNCA: instanciar manualmente en el router
    ...
```

---

## 7. Strategy Pattern — LLM Adapters

### Qué es

El Strategy Pattern define una familia de algoritmos intercambiables que implementan una interfaz común. En este proyecto, los adaptadores de LLM (Anthropic, OpenAI, Ollama) son estrategias intercambiables que el TutorService usa sin saber cuál está activo.

### Por qué se usa en este proyecto

1. **Vendor independence**: El sistema no está atado a Anthropic. Se puede cambiar a OpenAI o a un modelo local sin cambiar el TutorService.
2. **Testing**: En tests, se usa un `FakeLLMAdapter` que retorna respuestas predefinidas, sin llamadas reales a la API.
3. **A/B testing**: Se puede configurar qué modelo usa cada comisión.
4. **Fallback**: Si Anthropic falla, se puede cambiar automáticamente a OpenAI.

### Implementación con Protocol

```python
# backend/app/features/tutor/adapters.py
from typing import Protocol, AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMStreamChunk:
    text: str
    is_final: bool
    tokens_used: int | None = None
    model_version: str | None = None


class LLMAdapter(Protocol):
    """
    Protocol (interfaz) que todos los adaptadores de LLM deben implementar.
    El TutorService solo conoce este Protocol, nunca las implementaciones.
    """
    
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Retorna un async iterator de chunks para streaming token a token."""
        ...
    
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Retorna la respuesta completa (sin streaming)."""
        ...


# ── Adaptador Anthropic ───────────────────────────────────────────────────────

class AnthropicAdapter:
    """
    Adaptador para Claude de Anthropic.
    Usa la librería oficial anthropic[async].
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        
        kwargs = dict(
            model=self.model,
            messages=anthropic_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if system:
            kwargs["system"] = system

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield LLMStreamChunk(text=text, is_final=False)
            
            final = await stream.get_final_message()
            yield LLMStreamChunk(
                text="",
                is_final=True,
                tokens_used=final.usage.output_tokens,
                model_version=final.model
            )
    
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        chunks = []
        async for chunk in self.stream(messages, system=system, max_tokens=max_tokens, temperature=temperature):
            if not chunk.is_final:
                chunks.append(chunk.text)
        return "".join(chunks)


# ── Adaptador Fake para Tests ─────────────────────────────────────────────────

class FakeLLMAdapter:
    """
    Adaptador fake para tests. Retorna respuestas predefinidas.
    No hace llamadas HTTP.
    """
    
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or ["¿Qué pensás vos? ¿Cómo encarías el problema?"]
        self._call_count = 0
    
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMStreamChunk]:
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        
        for char in response:
            yield LLMStreamChunk(text=char, is_final=False)
        yield LLMStreamChunk(text="", is_final=True, tokens_used=len(response))
    
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return response


# ── Fábrica de Adaptadores ────────────────────────────────────────────────────

def create_llm_adapter(config) -> LLMAdapter:
    """Fábrica que retorna el adaptador configurado."""
    if config.LLM_PROVIDER == "anthropic":
        return AnthropicAdapter(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL
        )
    elif config.LLM_PROVIDER == "openai":
        return OpenAIAdapter(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL
        )
    elif config.LLM_PROVIDER == "ollama":
        return OllamaAdapter(base_url=config.OLLAMA_BASE_URL)
    else:
        raise ValueError(f"LLM provider desconocido: {config.LLM_PROVIDER}")
```

### Anti-patrón a Evitar

```python
# MAL: El service importa Anthropic directamente — está acoplado al vendor
class TutorService:
    async def stream_chat(self, messages):
        import anthropic  # NUNCA: acoplamiento directo
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        async with client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                yield text

# BIEN: El service usa el Protocol, no sabe qué adaptador está debajo
class TutorService:
    def __init__(self, llm: LLMAdapter):  # Recibe el Protocol
        self.llm = llm
    
    async def stream_chat(self, messages):
        async for chunk in self.llm.stream_chat(...):
            yield chunk
```

---

## 8. Guard / Policy Pattern

### Qué es

El Guard/Policy Pattern encapsula reglas de negocio en objetos dedicados. En el contexto del tutor socrático, los Guards son políticas que inspeccionan las respuestas del LLM antes de enviarlas al estudiante, bloqueando o modificando respuestas que violen los principios socráticos.

### Por qué se usa en este proyecto

El tutor socrático tiene una regla fundamental: **nunca dar soluciones directas al ejercicio**. Esta regla (guardrail anti-solver) necesita ser:
- **Configurable**: El administrador puede ajustar la sensibilidad desde `tutor_system_prompts.guardrails_config`
- **Auditable**: Cada bloqueo genera un `governance_event`
- **Composable**: Múltiples guards pueden aplicarse en cadena

### Implementación

```python
# backend/app/features/tutor/guardrails.py
from typing import Protocol
from dataclasses import dataclass
from enum import Enum


class GuardrailResult(Enum):
    PASS = "pass"
    BLOCK = "block"
    MODIFY = "modify"


@dataclass
class GuardrailDecision:
    result: GuardrailResult
    reason: str | None = None
    modified_content: str | None = None
    alternative_prompt: str | None = None


class GuardrailPolicy(Protocol):
    """Protocol que todos los guardrails implementan."""
    
    name: str
    
    async def evaluate(
        self,
        response: str,
        context: dict
    ) -> GuardrailDecision:
        """
        Evalúa si la respuesta pasa el guardrail.
        
        context contiene:
            - exercise: El ejercicio en cuestión
            - student_question: La pregunta del estudiante
            - session_history: Historial de la sesión
        """
        ...


# ── Anti-Solver Guard ─────────────────────────────────────────────────────────

class AntiSolverGuard:
    """
    Detecta si la respuesta del LLM contiene soluciones directas al ejercicio.
    
    Sensibilidades:
    - "low": Solo bloquea si la respuesta contiene código que resuelve el ejercicio
    - "medium": Bloquea si hay explicaciones paso a paso de la solución
    - "high": Bloquea ante cualquier indicio de solución directa
    """
    
    name = "AntiSolverGuard"
    
    # Patrones que indican solución directa (en español e inglés)
    SOLUTION_PATTERNS = [
        "la solución es",
        "el resultado es",
        "el código es:",
        "podés usar la función",
        "simplemente usá",
        "the answer is",
        "use the built-in",
        "just call",
    ]
    
    def __init__(self, config: dict):
        self.sensitivity = config.get("sensitivity", "medium")
        self.custom_patterns = config.get("forbidden_patterns", [])
        self.all_patterns = self.SOLUTION_PATTERNS + self.custom_patterns
    
    async def evaluate(
        self,
        response: str,
        context: dict
    ) -> GuardrailDecision:
        response_lower = response.lower()
        
        # Verificar patrones de solución directa
        for pattern in self.all_patterns:
            if pattern.lower() in response_lower:
                return GuardrailDecision(
                    result=GuardrailResult.BLOCK,
                    reason=f"La respuesta contiene el patrón '{pattern}' que indica solución directa.",
                    alternative_prompt=self._generate_socratic_redirect(context)
                )
        
        # En sensibilidad alta, verificar si hay código Python que parece solucionar
        if self.sensitivity == "high":
            if self._contains_solution_code(response, context):
                return GuardrailDecision(
                    result=GuardrailResult.BLOCK,
                    reason="La respuesta contiene código que podría resolver el ejercicio directamente.",
                    alternative_prompt=self._generate_socratic_redirect(context)
                )
        
        return GuardrailDecision(result=GuardrailResult.PASS)
    
    def _contains_solution_code(self, response: str, context: dict) -> bool:
        """Heurística simple: si hay un bloque de código y parece completo."""
        import re
        code_blocks = re.findall(r"```python(.*?)```", response, re.DOTALL)
        for block in code_blocks:
            # Si el bloque tiene return statement y más de 3 líneas, probablemente es solución
            if "return" in block and len(block.strip().split("\n")) > 3:
                return True
        return False
    
    def _generate_socratic_redirect(self, context: dict) -> str:
        """Genera una pregunta socrática de redirección."""
        return (
            "En lugar de darte la respuesta directamente, te hago una pregunta: "
            "¿Qué tendrías que comparar para saber cuál elemento es el más grande? "
            "Pensá en cómo lo harías con papel y lápiz primero."
        )


# ── Tone Guard ────────────────────────────────────────────────────────────────

class ToneGuard:
    """Verifica que el tono de la respuesta sea apropiado y socrático."""
    
    name = "ToneGuard"
    
    INAPPROPRIATE_TONES = [
        "¡Perfecto!",
        "¡Excelente trabajo!",
        "Estás equivocado",
        "Eso está mal",
    ]
    
    async def evaluate(self, response: str, context: dict) -> GuardrailDecision:
        for phrase in self.INAPPROPRIATE_TONES:
            if phrase in response:
                return GuardrailDecision(
                    result=GuardrailResult.MODIFY,
                    reason=f"Tono inapropiado: '{phrase}'",
                    modified_content=response.replace(phrase, "").strip()
                )
        return GuardrailDecision(result=GuardrailResult.PASS)


# ── Pipeline de Guardrails ────────────────────────────────────────────────────

class GuardrailsPipeline:
    """
    Aplica múltiples guardrails en cadena.
    El primer BLOCK detiene el pipeline.
    Los MODIFY se acumulan.
    """
    
    def __init__(self, guards: list[GuardrailPolicy]):
        self.guards = guards
    
    async def evaluate(
        self,
        response: str,
        context: dict
    ) -> tuple[str | None, str | None]:
        """
        Retorna:
            (response_final, None) si pasa todos los guards
            (None, alternative_prompt) si algún guard bloquea
        """
        current_response = response
        
        for guard in self.guards:
            decision = await guard.evaluate(current_response, context)
            
            if decision.result == GuardrailResult.BLOCK:
                # Registrar en governance_events
                await self._log_block(guard.name, decision, context)
                return None, decision.alternative_prompt
            
            elif decision.result == GuardrailResult.MODIFY:
                current_response = decision.modified_content
        
        return current_response, None
    
    async def _log_block(self, guard_name: str, decision: GuardrailDecision, context: dict):
        """Persiste el evento de bloqueo en governance_events."""
        # Se inyecta el governance_repo en la inicialización del pipeline
        pass


# ── Fábrica del Pipeline desde Config ────────────────────────────────────────

def build_guardrails_pipeline(guardrails_config: dict) -> GuardrailsPipeline:
    """
    Construye el pipeline de guardrails a partir de la configuración
    almacenada en tutor_system_prompts.guardrails_config
    """
    guards = []
    
    anti_solver_cfg = guardrails_config.get("anti_solver", {})
    if anti_solver_cfg.get("enabled", True):
        guards.append(AntiSolverGuard(anti_solver_cfg))
    
    tone_cfg = guardrails_config.get("tone", {})
    if tone_cfg.get("style") == "socratic":
        guards.append(ToneGuard())
    
    return GuardrailsPipeline(guards)
```

#### Uso en TutorService

```python
# backend/app/features/tutor/service.py
class TutorService:
    
    def __init__(self, llm: LLMAdapter, guardrails: GuardrailsPipeline):
        self.llm = llm
        self.guardrails = guardrails
    
    async def stream_with_guardrails(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        context: dict
    ) -> AsyncIterator[dict]:
        """
        Genera la respuesta del LLM con guardrails aplicados.
        Si el guardrail bloquea, emite el alternative_prompt en su lugar.
        """
        # Acumular la respuesta completa antes de aplicar guardrails
        full_response_chunks = []
        async for chunk in self.llm.stream_chat(system_prompt, messages):
            if not chunk.is_final:
                full_response_chunks.append(chunk.content)
        
        full_response = "".join(full_response_chunks)
        
        # Aplicar guardrails sobre la respuesta completa
        approved_response, alternative = await self.guardrails.evaluate(
            full_response, context
        )
        
        if approved_response is None:
            # Guardrail bloqueó — enviar el alternative_prompt
            yield {"type": "guardrail_blocked", "content": alternative}
        else:
            # Streaming de la respuesta aprobada
            for char in approved_response:
                yield {"type": "token", "text": char}
            yield {"type": "complete"}
```

### Anti-patrón a Evitar

```python
# MAL: Lógica de guardrails mezclada con lógica de streaming
class TutorService:
    async def stream_chat(self, messages):
        async for chunk in self.llm.stream_chat(...):
            # NUNCA: validar dentro del stream chunk a chunk
            if "la solución es" in chunk.content:
                yield {"type": "error", "content": "Bloqueado"}
                return
            yield {"type": "token", "text": chunk.content}
# Problema: no podés detectar patrones que se dividen en múltiples chunks

# BIEN: Acumular respuesta completa y aplicar guards sobre el texto íntegro
# (ver implementación de GuardrailsPipeline arriba)
```

---

## Resumen de Patrones

| Patrón | Dónde Vive | Beneficio Principal |
|--------|-----------|---------------------|
| Repository | `shared/repositories/` | Queries de dominio encapsuladas, testabilidad |
| Unit of Work | `shared/db/unit_of_work.py` | Transaccionalidad, sin commits accidentales |
| Domain Service | `features/*/service.py` | Lógica de negocio pura, sin HTTP |
| Event Bus | `core/event_bus.py` | Desacoplamiento inter-dominio |
| Hash Chain | `features/cognitive/hash_chain.py` | Integridad del CTR |
| Dependency Injection | `dependencies.py` + `Depends()` | Composición, testabilidad, sin globales |
| Strategy (LLM) | `features/tutor/adapters.py` | Vendor independence, fallback |
| Guard/Policy | `features/tutor/guardrails.py` | Guardrails componibles y auditables |

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0*
