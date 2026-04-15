## Context

El proyecto AI-Native es un sistema pedagógico para enseñanza de programación universitaria (UTN FRM). Actualmente el repositorio solo contiene documentación (knowledge-base, EPICs, guías). No existe código, infraestructura de desarrollo, ni pipelines de CI/CD. Esta EPIC establece toda la base desde cero.

El stack definido es:
- Backend: Python 3.12 + FastAPI + SQLAlchemy 2.0 async
- Frontend: React 19 + TypeScript + Zustand 5 + TailwindCSS 4 + Vite
- DB: PostgreSQL 16 con 4 schemas (operational, cognitive, governance, analytics)
- Cache/Event Bus: Redis 7 con Streams
- CI: GitHub Actions

## Goals / Non-Goals

**Goals:**
- Que `docker compose up` levante todo el stack de desarrollo en un solo comando
- Que un dev nuevo clone y tenga todo funcionando en < 10 minutos
- Que el CI valide lint + tests + build en cada PR
- Que el Event Bus via Redis Streams esté operativo para comunicación cross-fase
- Que la tabla `event_outbox` provea transactional reliability para eventos

**Non-Goals:**
- Implementar lógica de negocio (pertenece a EPICs 2-19)
- Deploy a producción o staging (será una EPIC separada)
- Configurar monitoring/observability avanzado
- Implementar autenticación (pertenece a EPIC-02)
- Crear modelos de dominio más allá de `event_outbox`

## Decisions

### 1. Monorepo con estructura flat

**Decisión**: Estructura `backend/`, `frontend/`, `shared/`, `infra/`, `devOps/` en la raíz del repo.

**Alternativas consideradas**:
- Workspaces con npm/pnpm: innecesario — el frontend es una sola app, no hay packages compartidos aún
- Repos separados por componente: overhead de CI/CD, versionado y coordinación entre repos para un equipo chico

**Rationale**: Un monorepo flat es lo más simple para un equipo universitario. La separación por directorios da claridad sin complejidad de tooling.

### 2. Docker Compose para desarrollo local

**Decisión**: Un único `docker-compose.yml` en `infra/` con 4 servicios: `db` (PostgreSQL 16), `redis` (Redis 7), `api` (FastAPI con hot reload via volume mounts), `frontend` (Vite dev server con HMR).

**Alternativas consideradas**:
- DevContainers: más setup inicial, no todos usan VS Code
- Servicios nativos (instalar PG y Redis localmente): inconsistencias entre devs, setup manual

**Rationale**: Docker Compose es el estándar de facto. Volume mounts para hot reload evitan rebuilds.

### 3. PostgreSQL con 4 schemas desde el inicio

**Decisión**: Crear los 4 schemas (`operational`, `cognitive`, `governance`, `analytics`) en la migración inicial, aunque solo `operational` se use en EPIC-01.

**Rationale**: Los schemas definen ownership por fase. Crearlos vacíos desde el inicio evita migraciones de renombrado y establece la convención.

### 4. Redis Streams sobre Pub/Sub para el Event Bus

**Decisión**: Redis Streams con consumer groups en vez de Pub/Sub simple.

**Alternativas consideradas**:
- Redis Pub/Sub: fire-and-forget, no persiste mensajes, si un consumer está caído pierde eventos
- RabbitMQ/Kafka: overkill para el volumen esperado de un aula universitaria

**Rationale**: Streams proveen persistencia, replay, consumer groups con acknowledgment, y backpressure. Todo lo que Pub/Sub no tiene, sin agregar una dependencia externa.

### 5. Outbox pattern para transactional events

**Decisión**: Tabla `event_outbox` en schema `operational`. Los servicios insertan eventos en la misma transacción que el cambio de estado. Un worker independiente lee la outbox y publica a Redis Streams.

**Rationale**: Garantiza consistencia entre estado de DB y eventos publicados. Evita el problema de "committed to DB but event lost".

### 6. Makefile como task runner

**Decisión**: `Makefile` en la raíz con targets: `dev`, `test`, `seed`, `lint`, `migrate`, `down`.

**Alternativas consideradas**:
- Just (justfile): más features pero requiere instalación extra
- npm scripts: solo cubren el frontend
- Shell scripts en `scripts/`: más verbose, menos discoverable

**Rationale**: Make está disponible en cualquier sistema Unix. Es simple, declarativo y universalmente conocido.

### 7. GitHub Actions con matrix strategy

**Decisión**: Un workflow que corre lint (ruff + mypy + eslint), tests (pytest + vitest) y build en paralelo usando matrix strategy.

**Rationale**: Paralelismo reduce tiempo de CI. Un solo workflow es más simple de mantener que múltiples.

## Risks / Trade-offs

- **[Docker performance en Windows/WSL2]** → Mitigación: documentar configuración óptima de WSL2 en onboarding; volume mounts con consistencia `cached`
- **[Redis Streams complexity para el equipo]** → Mitigación: clase `EventBus` abstrae la complejidad; los consumers solo implementan callbacks
- **[4 schemas vacíos generan confusión]** → Mitigación: migración inicial con comentarios explicativos sobre ownership por fase
- **[Outbox worker como proceso separado]** → Mitigación: en desarrollo corre como background task del FastAPI process; en producción será un worker separado
- **[Pre-commit hooks lentos]** → Mitigación: ruff es extremadamente rápido; mypy con cache incremental; hooks solo en archivos staged
