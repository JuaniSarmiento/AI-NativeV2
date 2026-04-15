## Why

La EPIC-01 dejó la infraestructura DevOps lista (Docker Compose, session factory, UoW, Alembic, event_outbox). Pero los modelos de dominio base — users, courses, commissions — no existen todavía. Sin ellos, ni auth (EPIC-03) ni el CRUD académico (EPIC-05) pueden arrancar. Esta EPIC establece los modelos fundacionales en el schema `operational` y el BaseRepository genérico que todas las fases van a heredar.

## What Changes

- Crear modelo `User` en schema `operational` (id UUID, email unique, password_hash, full_name, role enum, is_active, timestamps)
- Crear modelo `Course` en schema `operational` (id UUID, name, description, topic_taxonomy JSONB nullable, is_active, timestamps)
- Crear modelo `Commission` en schema `operational` (id UUID, course_id FK, teacher_id FK → users, name, year, semester, is_active, timestamps)
- Crear `BaseRepository` genérico async con CRUD base + selectinload
- Crear migración Alembic `002` con las 3 tablas nuevas
- Actualizar `alembic/env.py` para importar los modelos nuevos
- Crear infraestructura de seed data (scripts base + mecanismo de carga)
- Actualizar `conftest.py` para registrar los nuevos modelos

## Capabilities

### New Capabilities

- `domain-models-base`: Modelos SQLAlchemy fundacionales (User, Course, Commission) en schema operational con relaciones, constraints y typing completo
- `base-repository`: Repository genérico async con CRUD (create, get_by_id, list, update, soft_delete) + selectinload configurable
- `seed-data-infra`: Infraestructura de seed data con scripts base y mecanismo de carga extensible por EPIC

### Modified Capabilities

- `monorepo-structure`: Se agregan archivos de modelos y repositorios a la estructura existente

## Impact

- **Backend**: `backend/app/shared/models/`, `backend/app/shared/repositories/`, `backend/alembic/`
- **Base de datos**: 3 tablas nuevas en schema `operational` (users, courses, commissions)
- **Testing**: `conftest.py` actualizado para registrar modelos nuevos
- **Downstream**: Desbloquea EPIC-03 (auth, necesita User) y EPIC-05 (CRUD académico, necesita Course/Commission)
