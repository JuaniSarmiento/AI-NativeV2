## 1. Monorepo Structure

- [x] 1.1 Create canonical directory tree: `backend/app/{main.py,config.py,dependencies.py,core/,features/,shared/}`, `backend/{alembic/,tests/,pyproject.toml,Dockerfile}`
- [x] 1.2 Create frontend directory tree: `frontend/src/{main.tsx,App.tsx,config.ts,features/,shared/,styles/}`, `frontend/{public/,index.html,vite.config.ts,tsconfig.json,package.json}`
- [x] 1.3 Create `shared/`, `infra/`, `devOps/` directories with placeholder README files
- [x] 1.4 Create `backend/pyproject.toml` with FastAPI, SQLAlchemy 2.0 async, uvicorn, alembic, redis, pydantic-settings, bcrypt, python-jose dependencies
- [x] 1.5 Create `frontend/package.json` with React 19, TypeScript, Zustand 5, TailwindCSS 4, Vite, React Router dependencies

## 2. Backend Foundation

- [x] 2.1 Create `backend/app/main.py` with FastAPI app factory, CORS middleware, and router registration
- [x] 2.2 Create `backend/app/config.py` with pydantic-settings `Settings` class reading from environment
- [x] 2.3 Create `backend/app/core/exceptions.py` with base domain exceptions (DomainError, NotFoundError, ValidationError, AuthorizationError)
- [x] 2.4 Create `backend/app/core/logging.py` with structured JSON logger configuration
- [x] 2.5 Create `backend/app/shared/db/session.py` with async session factory (`expire_on_commit=False`)
- [x] 2.6 Create `backend/app/shared/db/base.py` with SQLAlchemy DeclarativeBase
- [x] 2.7 Create `backend/app/shared/db/unit_of_work.py` with async UoW context manager pattern
- [x] 2.8 Create `backend/app/dependencies.py` with shared Depends factories (get_db_session, get_settings)

## 3. Frontend Foundation

- [x] 3.1 Create `frontend/vite.config.ts` with React plugin, proxy to API at localhost:8000, and HMR config
- [x] 3.2 Create `frontend/src/main.tsx` with React 19 root rendering
- [x] 3.3 Create `frontend/src/App.tsx` with React Router setup and basic layout
- [x] 3.4 Create `frontend/src/config.ts` with environment variable reading (API URL)
- [x] 3.5 Create `frontend/src/styles/globals.css` with TailwindCSS 4 `@theme` config, dark mode CSS variables, and design tokens
- [x] 3.6 Create `frontend/src/shared/lib/logger.ts` with centralized logger (no direct console.*)
- [x] 3.7 Create `frontend/src/shared/lib/api-client.ts` with typed fetch wrapper for API calls
- [x] 3.8 Create `frontend/tsconfig.json` with strict mode and path aliases

## 4. Docker Compose & Environment

- [x] 4.1 Create `infra/docker-compose.yml` with 4 services: db (PostgreSQL 16), redis (Redis 7), api (FastAPI with hot reload), frontend (Vite dev server)
- [x] 4.2 Create `infra/init-db.sql` script to create 4 PostgreSQL schemas (operational, cognitive, governance, analytics)
- [x] 4.3 Create `backend/Dockerfile` for development (Python 3.12, volume mount for hot reload)
- [x] 4.4 Create `frontend/Dockerfile` for development (Node 20, volume mount for HMR)
- [x] 4.5 Update `env.example` with all required variables: DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, SECRET_KEY, and service ports with comments
- [x] 4.6 Configure named Docker volumes for PostgreSQL and Redis data persistence
- [x] 4.7 Add healthchecks for db and redis services

## 5. Alembic & Initial Migration

- [x] 5.1 Configure `backend/alembic.ini` and `backend/alembic/env.py` for async SQLAlchemy with target metadata
- [x] 5.2 Create initial migration: 4 schemas + `event_outbox` table in operational schema (id UUID PK, event_type VARCHAR(100), payload JSONB, status ENUM pending/processed/failed, processed_at TIMESTAMPTZ nullable, created_at TIMESTAMPTZ, retry_count SMALLINT default 0)

## 6. Event Bus Core

- [x] 6.1 Create `backend/app/core/event_bus.py` with `EventBus` class: `publish(stream, event_type, payload)` method using Redis Streams XADD
- [x] 6.2 Add `subscribe(stream, group, consumer, callback)` method with XREADGROUP, XACK, and exponential backoff on connection errors
- [x] 6.3 Create stream initialization utility that idempotently creates 4 streams (`events:submissions`, `events:tutor`, `events:code`, `events:cognitive`) with consumer groups
- [x] 6.4 Create `backend/app/shared/models/event_outbox.py` SQLAlchemy model for `event_outbox` table
- [x] 6.5 Create outbox worker that reads pending events, publishes to Redis Streams, and updates status (with retry_count limit of 5)

## 7. CI/CD Pipeline

- [x] 7.1 Create `.github/workflows/ci.yml` with trigger on PR to master
- [x] 7.2 Add backend lint job: ruff check + mypy on `backend/`
- [x] 7.3 Add frontend lint job: eslint + prettier --check on `frontend/`
- [x] 7.4 Add backend test job: pytest with PostgreSQL service container
- [x] 7.5 Add frontend test job: vitest run
- [x] 7.6 Add build verification job: backend import check + vite build

## 8. Dev Tooling

- [x] 8.1 Create `Makefile` with targets: dev, down, test, lint, seed, migrate
- [x] 8.2 Create `.pre-commit-config.yaml` with ruff, mypy, eslint, prettier hooks
- [x] 8.3 Create seed data script in `infra/seed/` with sample courses, commissions, students, exercises

## 9. Testing Foundation

- [x] 9.1 Create `backend/tests/conftest.py` with async session fixture, test client fixture, and test database setup
- [x] 9.2 Create `backend/tests/unit/test_event_bus.py` with tests for EventBus publish/subscribe
- [x] 9.3 Create `frontend/vitest.config.ts` and a smoke test to verify the test runner works
- [ ] 9.4 Verify `docker compose up` starts all services and healthchecks pass
