# EPIC-17: Remover MSW y Conectar APIs Reales

> **Issue**: #17 | **Milestone**: Integración y QA | **Labels**: epic, integration, priority:critical

## Contexto

Durante el desarrollo paralelo, el frontend trabajó contra MSW (Mock Service Worker). Ahora hay que remover los mocks y conectar con las APIs reales de Fases 1, 2 y 3. Este es el momento de la verdad: si los contratos se respetaron, debería ser plug-and-play. Si no, acá aparecen los problemas.

## Alcance

### Frontend
- Remover MSW handlers y dependencia
- Conectar cada feature con su API real:
  - Auth (EPIC-03) → ya conectado
  - Cursos/Comisiones (EPIC-05) → conectar
  - Ejercicios (EPIC-06) → conectar
  - Sandbox/Ejecución (EPIC-07) → conectar
  - Submissions (EPIC-08) → conectar
  - Chat tutor WebSocket (EPIC-09) → conectar
  - Reflexión (EPIC-12) → conectar
  - Dashboard docente (EPIC-14) → conectar
  - Risk table (EPIC-15) → conectar
  - Traza cognitiva (EPIC-16) → conectar
- Verificar que los schemas de respuesta coinciden con los tipos TypeScript
- Fix de discrepancias entre mock y API real

### Backend
- Verificar que todos los endpoints retornan el formato estándar
- Fix de inconsistencias descubiertas durante integración

## Contratos

### Produce
- Frontend funcionando contra backend real
- Lista de discrepancias encontradas (si las hay)

### Consume
- Todas las APIs de Fases 0-3

## Dependencias
- **Blocked by**: EPIC-05 a EPIC-16 (necesita todas las APIs implementadas)
- **Blocks**: EPIC-18 (E2E tests necesitan integración real)

## Stories

- [ ] Remover MSW handlers y dependencia de package.json
- [ ] Conectar auth flow (ya debería estar)
- [ ] Conectar cursos, comisiones, enrollments
- [ ] Conectar ejercicios y listados
- [ ] Conectar sandbox y ejecución
- [ ] Conectar submissions y snapshots
- [ ] Conectar chat WebSocket del tutor
- [ ] Conectar reflexión post-ejercicio
- [ ] Conectar dashboard docente (métricas, radar chart, risk table)
- [ ] Conectar traza cognitiva visual
- [ ] Verificar schemas de respuesta vs tipos TypeScript
- [ ] Fix de discrepancias encontradas

## Criterio de Done

- MSW completamente removido
- Todas las features funcionan contra APIs reales
- No hay errores de tipo en runtime
- Flujo end-to-end alumno funciona
- Flujo end-to-end docente funciona

## Referencia
- `knowledge-base/02-arquitectura/03_api_y_endpoints.md`
