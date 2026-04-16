## Context

Sistema integrado con frontend React en :5173 (proxy a backend :8000). Todos los endpoints funcionan, navegacion conectada. Necesitamos validar flujos completos con browser automation.

## Goals / Non-Goals

**Goals:**
- Validar flujo alumno E2E: register → login → enroll → actividad → codigo → ejecutar → submit → reflexion
- Validar flujo docente E2E: login → cursos → dashboard → correccion con IA → confirmar nota
- Validar RBAC: alumno no accede a rutas docente
- Setup reproducible con un solo comando

**Non-Goals:**
- CI/CD integration (se hace en EPIC-19)
- Tests de carga/stress
- Coverage de todos los edge cases

## Decisions

### D1: Playwright en directorio raiz `e2e/`
No dentro de frontend/ ni backend/ — los tests E2E son transversales. Config en raiz.

### D2: Seed de datos via API, no via DB
Los tests crean sus propios datos via endpoints (register, create course, etc.) para ser independientes del estado de la DB.

### D3: Tests secuenciales, no paralelos
Los flujos dependen unos de otros (alumno crea datos que docente consume). Se ejecutan en orden.
