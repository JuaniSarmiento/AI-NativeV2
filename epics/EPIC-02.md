# EPIC-02: Base de Datos y Schemas

> **Issue**: #2 | **Milestone**: Fase 0 — Fundación | **Labels**: epic, fase-0, priority:critical

## Contexto

Establece los 4 schemas de PostgreSQL que definen el ownership de datos por fase. Esta separación es una decisión arquitectónica CLAVE: cada fase es dueña de su schema y solo ella puede INSERT/UPDATE/DELETE. Otras fases leen via REST.

## Alcance

### Backend
- Configuración de SQLAlchemy 2.0 async (session factory, engine, DeclarativeBase)
- Creación de los 4 schemas: `operational`, `cognitive`, `governance`, `analytics`
- Alembic configurado con soporte multi-schema
- Migración inicial con tablas base (users, courses, commissions, event_outbox)
- Unit of Work pattern implementado
- Repository base genérico
- Fixtures de testing (`conftest.py` con async session, testcontainers)
- **Seed data scripts infrastructure**: mecanismo base para seed data (scripts, loaders, fixtures). Cada EPIC de dominio extiende el seed con sus propios datos específicos.

### Frontend
- Sin alcance frontend directo

## Contratos

### Produce
- `AsyncSession` factory via dependency injection
- `UnitOfWork` pattern para transacciones
- `BaseRepository` genérico que todas las fases heredan
- 4 schemas PostgreSQL listos para recibir modelos
- `conftest.py` con fixtures de testing reutilizables
- Infraestructura de seed data que otras EPICs extienden

### Consume
- Docker Compose con PostgreSQL (de EPIC-01)

### Modelos (owner — schema: operational)
- `users`: id (UUID PK), email (VARCHAR, UNIQUE), password_hash (VARCHAR 128), full_name (VARCHAR), role (ENUM: alumno/docente/admin), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- `courses`: id (UUID PK), name (VARCHAR 255), description (TEXT), topic_taxonomy (JSONB, NULLABLE — árbol de temas del curso), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- `commissions`: id (UUID PK), course_id (UUID FK → courses.id, NOT NULL), teacher_id (UUID FK → users.id, NOT NULL — el docente responsable de la comisión), name (VARCHAR), year (SMALLINT), semester (SMALLINT), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
- `event_outbox`: id (UUID PK), event_type (VARCHAR 100), payload (JSONB), status (ENUM: pending/processed/failed), processed_at (TIMESTAMPTZ nullable), created_at (TIMESTAMPTZ), retry_count (SMALLINT default 0)

## Dependencias
- **Blocked by**: EPIC-01 (necesita Docker Compose con PostgreSQL)
- **Blocks**: EPIC-03 (auth necesita modelo users), EPIC-05 (CRUD académico usa modelos y sesión DB)

## Stories

- [ ] SQLAlchemy 2.0 async: engine, session factory, DeclarativeBase con `expire_on_commit=False`
- [ ] Crear 4 schemas PostgreSQL: operational, cognitive, governance, analytics
- [ ] Alembic configurado con multi-schema y auto-generate
- [ ] Migración inicial: tabla `users` en schema `operational` con todos los campos
- [ ] Migración: tabla `courses` con campo `topic_taxonomy (JSONB, NULLABLE)`
- [ ] Migración: tabla `commissions` con `teacher_id (UUID FK → users.id, NOT NULL)`
- [ ] Migración: tabla `event_outbox` (ver EPIC-01 para schema completo)
- [ ] Unit of Work pattern (context manager async)
- [ ] BaseRepository genérico (CRUD base + selectinload)
- [ ] `conftest.py` con fixtures: async session, test client HTTPX, cleanup
- [ ] Infraestructura de seed data: scripts base y mecanismo de carga

## Criterio de Done

- Los 4 schemas existen en PostgreSQL
- Modelos `users`, `courses`, `commissions`, `event_outbox` migrados y funcionando
- UoW y BaseRepository testeados con integration tests
- `conftest.py` permite correr tests async contra DB real
- Seed data base cargable con un comando

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/02-arquitectura/04_patrones_de_diseno.md`
- `knowledge-base/04-infraestructura/04_migraciones.md`
