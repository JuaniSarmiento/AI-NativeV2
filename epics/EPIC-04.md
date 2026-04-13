# EPIC-04: Contratos OpenAPI, MSW y Design System

> **Issue**: #4 | **Milestone**: Fase 0 — Fundación | **Labels**: epic, fase-0, priority:high

## Contexto

Establece los contratos que permiten desarrollo paralelo sin sorpresas de integración. OpenAPI spec define los endpoints, MSW permite al frontend trabajar sin backend real, y el Design System garantiza consistencia visual. El App Shell define la estructura de navegación sobre la que todas las EPICs de feature montan sus componentes.

## Alcance

### Backend
- OpenAPI spec auto-generado desde FastAPI (`/openapi.json`)
- Schemas Pydantic para respuesta estándar: `{ status, data, meta, errors }`
- Healthcheck endpoints: `GET /health`, `GET /health/full`

### Frontend
- MSW (Mock Service Worker) configurado con handlers basados en OpenAPI spec
- Design System base en TailwindCSS 4:
  - Design tokens via CSS custom properties en `@theme`
  - Paleta de colores con dark mode (`dark:` variant)
  - Tipografía, spacing, border-radius tokens
  - Componentes base: Button, Input, Card, Modal, DataTable
- Logger centralizado (reemplaza `console.*`)
- Configuración de Vitest para testing frontend
- **App Shell / Layout / Routing**:
  - Componente de layout principal (sidebar, header, área de contenido)
  - Configuración de React Router con definición de rutas por rol
  - Estructura de navegación: rutas de alumno vs rutas de docente/admin
  - Layout switcher basado en el rol del usuario autenticado
  - Este shell es el punto de montaje para todos los componentes de EPICs de feature

## Contratos

### Produce
- OpenAPI spec como fuente de verdad para endpoints
- MSW handlers que el frontend usa durante desarrollo paralelo
- Design tokens y componentes base que todas las EPICs de frontend usan
- Formato de respuesta estándar que todos los endpoints respetan
- App Shell (`AppLayout`) como componente raíz que todas las features montan
- Configuración de React Router con rutas protegidas por rol
- Layout switcher (`AlumnoLayout` / `DocenteLayout` / `AdminLayout`)

### Consume
- FastAPI app configurada (de EPIC-01)

### Modelos
- Ninguno nuevo

## Dependencias
- **Blocked by**: EPIC-01 (necesita la app FastAPI base y estructura de directorios)
- **Blocks**: EPIC-05 (primer consumidor directo del Design System, contratos OpenAPI y App Shell)

## Stories

- [ ] OpenAPI spec auto-generado y validado
- [ ] Schema de respuesta estándar (`ApiResponse`, `PaginatedResponse`, `ErrorResponse`)
- [ ] Healthcheck endpoints (`/health`, `/health/full`)
- [ ] MSW configurado con handlers base (auth endpoints como ejemplo)
- [ ] Design tokens en `globals.css` con `@theme` (colores, tipografía, spacing)
- [ ] Dark mode con swap de CSS variables
- [ ] Componentes base: Button, Input, Card, Modal
- [ ] Logger centralizado frontend
- [ ] Vitest configurado con setup
- [ ] Componente `AppLayout` con sidebar, header y área de contenido
- [ ] React Router configurado con rutas por rol (alumno / docente / admin)
- [ ] Layout switcher basado en rol del usuario autenticado
- [ ] Rutas protegidas integradas con el shell (redirect a login si no autenticado)

## Criterio de Done

- `/openapi.json` refleja todos los endpoints existentes
- MSW intercepta requests en desarrollo y retorna datos mock coherentes
- Design System tiene tokens + dark mode + componentes base usables
- Vitest corre tests del frontend
- App Shell renderiza correctamente el layout según el rol del usuario
- React Router navega entre secciones sin recargar la página

## Referencia
- `knowledge-base/02-arquitectura/03_api_y_endpoints.md`
- `knowledge-base/05-dx/04_convenciones_y_estandares.md`
