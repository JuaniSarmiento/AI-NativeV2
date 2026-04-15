## Why

Las EPICs 1-3 dejaron la infra, modelos base, y auth funcional. Pero el frontend no tiene componentes reutilizables, no tiene layouts por rol, y no tiene MSW para desarrollo paralelo. Cada EPIC de feature va a necesitar Button, Input, Card, Modal, un App Shell con sidebar, y rutas protegidas por rol. Sin esta EPIC, cada feature re-inventa la rueda.

## What Changes

### Backend
- Schema Pydantic de respuesta estándar reutilizable (`StandardResponse`, `PaginatedResponse`)
- Endpoint `GET /api/v1/health/full` con estado de DB y Redis

### Frontend
- MSW (Mock Service Worker) con handlers para auth endpoints
- Componentes base premium: Button, Input, Card, Modal
- App Shell: `AppLayout` con sidebar responsive, header, area de contenido
- Layouts por rol: `AlumnoLayout`, `DocenteLayout` (distintas rutas de sidebar)
- React Router con rutas por rol integradas al shell
- Vitest smoke test funcional

## Capabilities

### New Capabilities
- `response-schemas`: Schemas Pydantic estándar para respuestas API (StandardResponse, PaginatedResponse, ErrorDetail)
- `health-full`: Endpoint de health check completo con estado de DB y Redis
- `msw-handlers`: Mock Service Worker configurado con handlers base para desarrollo paralelo
- `design-system-components`: Componentes base premium (Button, Input, Card, Modal) con design tokens
- `app-shell`: Layout principal con sidebar, header, routing por rol, y layout switcher

### Modified Capabilities
- `monorepo-structure`: Se agregan componentes shared, MSW config, y layouts de app shell

## Impact

- **Backend**: `backend/app/shared/schemas/`, `backend/app/main.py` (health/full)
- **Frontend**: `frontend/src/shared/components/`, `frontend/src/features/*/layouts/`, `frontend/src/App.tsx`
- **Dev tooling**: MSW en `frontend/src/mocks/`
- **Downstream**: Todas las EPICs de feature montan sobre este shell y reutilizan componentes
