## ADDED Requirements

### Requirement: Docker Compose orchestrates full stack
A single `docker-compose.yml` SHALL define services for PostgreSQL 16, Redis 7, the FastAPI backend API, and the Vite frontend dev server.

#### Scenario: Full stack starts with one command
- **WHEN** a developer runs `docker compose up`
- **THEN** all 4 services (db, redis, api, frontend) SHALL start and become healthy within 60 seconds

#### Scenario: Services are accessible on defined ports
- **WHEN** all services are running
- **THEN** the API SHALL be reachable at `localhost:8000`, the frontend at `localhost:5173`, PostgreSQL at `localhost:5432`, and Redis at `localhost:6379`

### Requirement: Backend hot reload via volume mounts
The API service SHALL mount the `backend/` directory as a volume and use a file watcher (uvicorn --reload) so code changes are reflected without container restarts.

#### Scenario: Code change triggers reload
- **WHEN** a developer modifies a Python file in `backend/app/`
- **THEN** uvicorn SHALL detect the change and reload the application within 3 seconds

### Requirement: Frontend HMR via Vite
The frontend service SHALL run Vite dev server with Hot Module Replacement enabled, with the source directory mounted as a volume.

#### Scenario: Component change triggers HMR
- **WHEN** a developer modifies a `.tsx` file in `frontend/src/`
- **THEN** Vite SHALL apply the change in the browser without a full page reload

### Requirement: PostgreSQL with 4 schemas
The PostgreSQL service SHALL initialize with 4 schemas: `operational`, `cognitive`, `governance`, and `analytics`.

#### Scenario: Schemas exist on first boot
- **WHEN** the PostgreSQL container starts for the first time
- **THEN** all 4 schemas SHALL be created via an init script before the API connects

### Requirement: Persistent volumes for data
Database and Redis data SHALL persist across container restarts using named Docker volumes.

#### Scenario: Data survives restart
- **WHEN** a developer runs `docker compose down` followed by `docker compose up`
- **THEN** PostgreSQL data and Redis data SHALL be preserved

#### Scenario: Full reset is available
- **WHEN** a developer runs `docker compose down -v`
- **THEN** all volumes SHALL be removed and the next `up` starts with a clean state

### Requirement: Environment variable configuration
All services SHALL read configuration from environment variables defined in a `.env` file, with `env.example` as the documented template.

#### Scenario: env.example is complete
- **WHEN** a developer copies `env.example` to `.env`
- **THEN** all services SHALL start without requiring additional configuration for local development
