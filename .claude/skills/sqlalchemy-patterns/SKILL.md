---
name: sqlalchemy-patterns
description: >
  Impone patrones seguros de SQLAlchemy 2.0 async: repositorios con selectinload,
  Unit of Work como context manager, comparaciones booleanas correctas, prevención
  de N+1 y modelos multi-schema. Trigger: al trabajar con modelos SQLAlchemy,
  repositorios o queries de la plataforma AI-Native.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o modificar modelos SQLAlchemy (`models/`)
- Al implementar repositorios (`repositories/`)
- Al escribir queries con `select()`, `join()`, o `subquery()`
- Al manejar transacciones o commits
- Al agregar relaciones entre modelos (eager vs lazy loading)
- Al definir modelos en schemas de PostgreSQL distintos del público

## Patrones Críticos

### 1. Repositorio con selectinload y paginación

Todas las relaciones se cargan explícitamente. Nunca se accede a atributos
relacionados sin haberlos incluido en el `options()` del query.

```python
# repositories/session_repository.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.session import LearningSession
from app.schemas.pagination import Page, PageParams

class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_with_interactions(self, session_id: str) -> LearningSession | None:
        stmt = (
            select(LearningSession)
            .where(LearningSession.id == session_id)
            .options(
                selectinload(LearningSession.interactions),
                selectinload(LearningSession.evaluations),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, params: PageParams) -> Page[LearningSession]:
        count_stmt = (
            select(func.count())
            .select_from(LearningSession)
            .where(LearningSession.is_active.is_(True))
        )
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(LearningSession)
            .where(LearningSession.is_active.is_(True))
            .options(selectinload(LearningSession.interactions))
            .offset(params.offset)
            .limit(params.size)
            .order_by(LearningSession.created_at.desc())
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return Page(items=list(rows), total=total, params=params)
```

### 2. Unit of Work como context manager

Un UoW por request. El commit y el rollback los maneja el UoW, nunca el servicio
ni el repositorio directamente.

```python
# database/unit_of_work.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.repositories.session_repository import SessionRepository
from app.repositories.evaluation_repository import EvaluationRepository

class UnitOfWork:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._factory()
        self.sessions = SessionRepository(self._session)
        self.evaluations = EvaluationRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()

# uso en servicio
async def close_session(self, session_id: str) -> None:
    async with self._uow as uow:
        session = await uow.sessions.get_with_interactions(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        session.close()  # mutación del modelo
        # commit automático al salir del context manager
```

### 3. Comparaciones booleanas seguras: `.is_(True)` no `== True`

SQLAlchemy 2.0 emite warnings con `== True`/`== False`. El operador correcto
produce SQL `IS TRUE` / `IS FALSE` que maneja NULLs correctamente.

```python
# models/session.py — columna booleana
from sqlalchemy.orm import Mapped, mapped_column

class LearningSession(Base):
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_flagged: Mapped[bool | None] = mapped_column(default=None)

# repositories — filtrado correcto
stmt = select(LearningSession).where(
    LearningSession.is_active.is_(True),       # correcto
    LearningSession.is_flagged.is_not(True),   # correcto para nullable
)

# NO usar:
# LearningSession.is_active == True             ← genera warning SAWarning
# LearningSession.is_flagged != True            ← no maneja NULL
```

### 4. Modelo multi-schema con `__table_args__`

Los modelos del dominio cognitivo viven en el schema `cognitive` de PostgreSQL.
Siempre declarar el schema en `__table_args__` para que Alembic y SQLAlchemy
generen el DDL correcto.

```python
# models/evaluation.py
from sqlalchemy import String, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class N4Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        Index("ix_eval_session_created", "session_id", "created_at"),
        {"schema": "cognitive"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("cognitive.learning_sessions.id"), nullable=False
    )
    n4_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    session: Mapped["LearningSession"] = relationship(back_populates="evaluations")
```

## Anti-patrones

### Commit directo desde el repositorio o servicio

```python
# NO — el repositorio hace commit, rompe la transacción del UoW
class SessionRepository:
    async def save(self, session: LearningSession) -> None:
        self._db.add(session)
        await self._db.commit()   # ← MAL: quema la transacción

# SI — solo flush si se necesita el ID generado; el commit lo hace el UoW
class SessionRepository:
    async def save(self, session: LearningSession) -> None:
        self._db.add(session)
        await self._db.flush()   # obtiene el ID sin commitear
```

### Comparación booleana con `== True`

```python
# NO
stmt = select(Session).where(Session.is_active == True)   # SAWarning + SQL incorrecto

# SI
stmt = select(Session).where(Session.is_active.is_(True))
```

### Relaciones sin estrategia de carga (N+1)

```python
# NO — acceso a relación lazy dentro de un loop async: N+1 garantizado
sessions = (await db.execute(select(LearningSession))).scalars().all()
for s in sessions:
    print(s.interactions)   # ← dispara 1 query extra por sesión

# SI — eager load explícito en el query
stmt = select(LearningSession).options(selectinload(LearningSession.interactions))
sessions = (await db.execute(stmt)).scalars().all()
for s in sessions:
    print(s.interactions)   # ya cargado, 0 queries extra
```

### Sesión síncrona en contexto async

```python
# NO
from sqlalchemy.orm import Session   # sesión síncrona
async def get_session(db: Session):  # ← bloquea el event loop
    return db.get(LearningSession, id)

# SI
from sqlalchemy.ext.asyncio import AsyncSession
async def get_session(db: AsyncSession):
    return await db.get(LearningSession, id)
```

## Checklist

- [ ] Toda relación accedida en el servicio está en `selectinload()` del query
- [ ] `commit()` y `rollback()` solo se llaman desde el UoW, nunca desde repos
- [ ] Filtros booleanos usan `.is_(True)` / `.is_(False)` / `.is_not(True)`
- [ ] Modelos en schemas no-public declaran `{"schema": "nombre"}` en `__table_args__`
- [ ] Los `ForeignKey` en schemas no-public incluyen el prefijo `"schema.tabla"`
- [ ] Los índices críticos están declarados en `__table_args__` junto al schema
- [ ] La paginación usa `func.count()` para el total, no `len(results)`
- [ ] Las `async_sessionmaker` se crean una vez en startup, no por request
