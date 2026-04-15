## Context

La EPIC-01 estableció la infraestructura: Docker Compose, SQLAlchemy async (session factory con `expire_on_commit=False`), UoW pattern, Alembic con soporte multi-schema, y la migración inicial (4 schemas + event_outbox). El codebase tiene directorios placeholder para features (courses, exercises, auth, etc.) pero sin modelos de dominio.

Estado actual relevante:
- `backend/app/shared/db/base.py` — `Base` con `DeclarativeBase`, naming conventions, type_annotation_map
- `backend/app/shared/db/session.py` — async engine + session factory
- `backend/app/shared/db/unit_of_work.py` — `AsyncUnitOfWork` context manager
- `backend/app/shared/models/event_outbox.py` — único modelo existente
- `backend/app/shared/repositories/` — solo `__init__.py`
- `backend/alembic/versions/001_initial_schemas_and_outbox.py` — schemas + event_outbox
- `backend/tests/conftest.py` — fixtures async con rollback per-test

## Goals / Non-Goals

**Goals:**
- Crear modelos User, Course, Commission con relaciones, constraints y schema assignment correcto
- Implementar BaseRepository genérico async que encapsule CRUD + selectinload
- Generar migración Alembic 002 con las 3 tablas nuevas
- Establecer infraestructura de seed data extensible
- Que todo sea testeable contra DB real (no mocks)

**Non-Goals:**
- No implementar endpoints REST (eso es EPIC-05)
- No implementar auth/JWT/login (eso es EPIC-03)
- No implementar modelos de otras fases (exercises, submissions, cognitive_*, tutor_*)
- No implementar lógica de negocio en los modelos — solo estructura de datos y relaciones

## Decisions

### D1: Modelos en `shared/models/` con archivos por tabla

Los modelos fundacionales (User, Course, Commission) van en `backend/app/shared/models/` porque son compartidos entre múltiples features. Cada modelo en su propio archivo (`user.py`, `course.py`, `commission.py`).

**Alternativa descartada**: Modelos dentro de cada feature folder (`features/auth/models.py`, `features/courses/models.py`). Descartada porque User es usado por auth, courses, commissions, enrollments, submissions — ponerlo en una feature genera imports circulares.

### D2: Role como PostgreSQL ENUM nativo

El campo `role` en User usa `sa.Enum('alumno', 'docente', 'admin', name='user_role', schema='operational')` — un ENUM nativo de PostgreSQL. Más eficiente en storage y validación que un VARCHAR con check constraint.

**Alternativa descartada**: Python Enum + VARCHAR. Descartada porque pierde la validación a nivel DB y ocupa más espacio.

### D3: BaseRepository con generics de Python

`BaseRepository[ModelType]` usa `typing.Generic` para tipar el modelo. Métodos: `get_by_id()`, `list()` (con paginación), `create()`, `update()`, `soft_delete()`. Todas las queries usan `selectinload()` configurable via parámetro `load_options`.

**Alternativa descartada**: Repositorios sin base genérica (cada repo implementa su CRUD). Descartada porque genera duplicación masiva de código boilerplate.

### D4: Soft delete con `is_active` boolean

Todos los modelos base usan `is_active: bool = True`. El BaseRepository filtra por `is_active.is_(True)` por defecto en `list()` y `get_by_id()`, con parámetro `include_inactive=False` para override.

### D5: Seed data como scripts Python con función `seed()`

Archivos en `infra/seed/` con un runner que ejecuta cada seed en orden. Cada EPIC futura agrega su propio archivo de seed. Se ejecuta via `make seed`.

**Alternativa descartada**: SQL files o fixtures YAML. Descartado porque los scripts Python pueden usar los modelos SQLAlchemy directamente y validar con Pydantic.

### D6: Migración manual (no auto-generate) para la 002

La migración 002 se escribe manualmente para tener control explícito sobre indexes, constraints y el schema assignment. Alembic auto-generate a veces omite detalles de schemas específicos.

## Risks / Trade-offs

- **[Risk] Circular imports entre modelos** → Mitigation: todos los modelos importan Base de `shared/db/base.py`. Las relaciones usan strings para lazy evaluation (`relationship("Commission", back_populates="course")`).
- **[Risk] BaseRepository demasiado genérico** → Mitigation: repos concretos pueden override cualquier método. El base solo cubre el 80% de casos comunes.
- **[Risk] ENUM nativo difícil de migrar** → Mitigation: agregar valores a un ENUM de PostgreSQL requiere un `ALTER TYPE`, pero para los 3 roles base es estable. Si se necesitan roles dinámicos, se migra a una tabla de roles (decisión futura).
- **[Risk] Seed data hard-coded** → Mitigation: los seeds son solo para desarrollo. Producción usa migraciones para datos base.
