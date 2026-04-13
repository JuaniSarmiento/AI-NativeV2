# EPIC-01: Infraestructura y DevOps

> **Issue**: #1 | **Milestone**: Fase 0 — Fundación | **Labels**: epic, fase-0, priority:critical

## Contexto

Primera EPIC del proyecto. Establece la infraestructura base que todas las fases necesitan para trabajar sin bloquearse. Sin esto, nadie arranca.

## Alcance

### Backend
- Monorepo con estructura `backend/`, `frontend/`, `shared/`, `infra/`, `devOps/`
- `docker-compose.yml` con PostgreSQL 16 + Redis 7 + API + Frontend con hot reload
- Scripts de seed data básico
- `env.example` completo y documentado
- `Makefile` o scripts de conveniencia (`make dev`, `make test`, `make seed`)
- **Event Bus core infrastructure**: topología Redis Streams para comunicación entre fases.
  - Creación de los 4 streams: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`
  - Scripts de inicialización de consumer groups por stream
  - Clase `EventBus` en `app/core/event_bus.py` con métodos `publish()`, `subscribe()`, y manejo de errores de conexión

### Frontend
- Proyecto Vite + React 19 + TypeScript + TailwindCSS 4 inicializado
- Hot reload configurado contra Docker Compose

### DevOps
- Pipeline CI/CD en GitHub Actions: lint + tests + build
- Pre-commit hooks (ruff, mypy, eslint, prettier)

## Contratos

### Produce
- Estructura de directorios canónica que todas las EPICs usan
- Docker Compose funcional para desarrollo local
- CI pipeline que valida PRs
- `EventBus` class (`app/core/event_bus.py`) disponible para todas las fases que publican/consumen eventos
- 4 Redis Streams configurados y listos: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`
- Tabla `operational.event_outbox` para el patrón outbox (transaccional reliability)

### Consume
- Nada (es la primera EPIC)

### Modelos (owner — schema: operational)
- `event_outbox`: id (UUID PK), event_type (VARCHAR 100), payload (JSONB), status (ENUM: pending/processed/failed), processed_at (TIMESTAMPTZ nullable), created_at (TIMESTAMPTZ), retry_count (SMALLINT default 0)

## Dependencias
- **Blocked by**: Nada
- **Blocks**: Todas las demás EPICs

## Stories

- [ ] Setup monorepo con estructura canónica de directorios
- [ ] Docker Compose: PostgreSQL 16 + Redis 7 + API (FastAPI) + Frontend (Vite) con hot reload
- [ ] `env.example` completo con todas las variables necesarias
- [ ] Scripts de conveniencia (`make dev`, `make test`, `make seed`)
- [ ] CI pipeline en GitHub Actions (lint + tests + build)
- [ ] Pre-commit hooks configurados (ruff, mypy, eslint, prettier)
- [ ] Crear los 4 Redis Streams con sus consumer groups (`events:submissions`, `events:tutor`, `events:code`, `events:cognitive`)
- [ ] Implementar clase `EventBus` en `app/core/event_bus.py` con `publish()` y `subscribe()`
- [ ] Migración inicial: tabla `event_outbox` en schema `operational`

## Criterio de Done

- `docker compose up` levanta API + DB + Redis + Frontend en un comando
- Un dev nuevo puede clonar y tener todo funcionando en < 10 minutos
- CI pasa lint + tests + build en cada PR
- Los 4 Redis Streams existen y tienen consumer groups configurados
- `EventBus` puede publicar un mensaje de prueba y un consumer lo recibe correctamente

## Referencia
- `knowledge-base/04-infraestructura/01_configuracion.md`
- `knowledge-base/05-dx/01_onboarding.md`
- `knowledge-base/05-dx/02_tooling.md`
