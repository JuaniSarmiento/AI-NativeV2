## ADDED Requirements

### Requirement: Canonical directory structure
The repository SHALL have the following top-level directories: `backend/`, `frontend/`, `shared/`, `infra/`, `devOps/`. Each directory SHALL serve a single purpose and contain only files relevant to its domain.

#### Scenario: Backend structure exists
- **WHEN** a developer inspects the `backend/` directory
- **THEN** it SHALL contain `app/` (with `main.py`, `config.py`, `dependencies.py`, `core/`, `features/`, `shared/`), `alembic/`, `tests/`, `pyproject.toml`, and `Dockerfile`

#### Scenario: Frontend structure exists
- **WHEN** a developer inspects the `frontend/` directory
- **THEN** it SHALL contain `src/` (with `main.tsx`, `App.tsx`, `config.ts`, `features/`, `shared/`, `styles/`), `public/`, `index.html`, `vite.config.ts`, `tsconfig.json`, and `package.json`

#### Scenario: Shared directory for contracts
- **WHEN** a developer inspects the `shared/` directory
- **THEN** it SHALL contain shared type definitions and OpenAPI contract schemas used by both backend and frontend

#### Scenario: Infra directory for orchestration
- **WHEN** a developer inspects the `infra/` directory
- **THEN** it SHALL contain `docker-compose.yml`, seed data scripts, and any orchestration configuration

#### Scenario: DevOps directory for deployment
- **WHEN** a developer inspects the `devOps/` directory
- **THEN** it SHALL contain Docker configuration files, nginx config templates, and deployment scripts

### Requirement: Backend feature module structure
Each feature module under `backend/app/features/` SHALL follow a consistent internal structure with `router.py`, `service.py`, `schemas.py`, and optionally `repository.py` and `dependencies.py`.

#### Scenario: Feature module is self-contained
- **WHEN** a new feature module is created (e.g., `auth/`)
- **THEN** it SHALL contain at minimum `router.py`, `service.py`, and `schemas.py` following the domain service pattern

### Requirement: Frontend feature folder structure
Each feature folder under `frontend/src/features/` SHALL contain components, hooks, and types specific to that feature domain.

#### Scenario: Feature folder isolation
- **WHEN** a developer creates a new frontend feature (e.g., `student/`)
- **THEN** it SHALL be self-contained with its own components, hooks, and types, importing only from `shared/` for cross-cutting concerns
