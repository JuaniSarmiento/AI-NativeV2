## Why

El proyecto AI-Native no tiene infraestructura de desarrollo. Sin una estructura de repositorio canónica, contenedores de desarrollo, CI/CD ni event bus, ninguna de las 18 EPICs restantes puede arrancar. Esta es la EPIC fundacional (Fase 0) que desbloquea todo el desarrollo posterior.

## What Changes

- Crear la estructura canónica del monorepo: `backend/`, `frontend/`, `shared/`, `infra/`, `devOps/`
- Configurar Docker Compose con PostgreSQL 16, Redis 7, API FastAPI y Frontend Vite con hot reload
- Crear `env.example` completo y documentado con todas las variables necesarias
- Implementar `Makefile` con scripts de conveniencia (`make dev`, `make test`, `make seed`)
- Configurar CI/CD pipeline en GitHub Actions: lint + tests + build
- Configurar pre-commit hooks: ruff, mypy, eslint, prettier
- Implementar Event Bus core con Redis Streams (4 streams: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`)
- Crear clase `EventBus` en `app/core/event_bus.py` con `publish()` y `subscribe()`
- Crear tabla `event_outbox` en schema `operational` para outbox pattern
- Crear seed data scripts iniciales

## Capabilities

### New Capabilities
- `monorepo-structure`: Estructura canónica del repositorio con separación backend/frontend/shared/infra/devOps
- `docker-dev-environment`: Docker Compose para desarrollo local con PostgreSQL 16 + Redis 7 + API + Frontend y hot reload
- `ci-cd-pipeline`: GitHub Actions pipeline con lint, tests y build para validar PRs
- `dev-tooling`: Makefile, pre-commit hooks (ruff, mypy, eslint, prettier), env.example y scripts de conveniencia
- `event-bus-core`: Redis Streams event bus con 4 streams, consumer groups, clase EventBus y tabla event_outbox

### Modified Capabilities
<!-- No hay capabilities existentes para modificar - este es el primer change -->

## Impact

- **Código**: Se crea toda la estructura base del proyecto desde cero (backend FastAPI, frontend Vite+React 19, shared contracts)
- **Infraestructura**: Docker Compose, PostgreSQL 16 con 4 schemas (operational, cognitive, governance, analytics), Redis 7
- **CI/CD**: Nuevo pipeline en `.github/workflows/`
- **DX**: Pre-commit hooks, Makefile, env.example; cualquier dev nuevo puede clonar y arrancar en < 10 minutos
- **Dependencias**: Python 3.12+, Node.js 20+, Docker + Docker Compose
- **Downstream**: Bloquea EPIC-02 a EPIC-19; todas dependen de esta infraestructura
