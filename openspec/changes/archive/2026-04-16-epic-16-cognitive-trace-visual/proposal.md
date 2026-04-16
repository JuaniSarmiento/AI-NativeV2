## Why

El sistema registra toda la actividad cognitiva del alumno (CTR events, code snapshots, chat, metricas) pero no hay forma de visualizarla. El docente necesita "ver la pelicula" de como un alumno trabajo en un ejercicio para entender su proceso cognitivo real — no solo el resultado. Ademas, la verificacion de integridad del hash chain existe como endpoint pero no tiene UI, y los eventos de governance (violaciones de guardrails, cambios de prompts) no se visualizan.

## What Changes

- 3 nuevos endpoints backend: traza completa unificada, timeline cronologico, evolucion de codigo con diffs
- 1 endpoint nuevo de governance: historial de prompts con hashes
- Frontend: pagina completa de traza cognitiva para docente con timeline vertical color-coded por N1-N4, panel de codigo evolutivo (diffs), panel de chat del tutor, metricas de sesion, indicador de integridad hash chain
- Frontend: vista de patrones de ejercicio a nivel clase (distribucion de estrategias, patrones de error)
- Frontend: reportes de governance (violaciones, prompt history, alertas de integridad)
- Nueva ruta `/teacher/trace/:sessionId` en el frontend

## Capabilities

### New Capabilities
- `cognitive-trace-api`: Endpoints de traza completa, timeline y code evolution para una sesion cognitiva
- `governance-prompts-api`: Endpoint de historial de prompts con hashes para admin
- `cognitive-trace-frontend`: Pagina visual de traza cognitiva (timeline N1-N4, code diffs, chat, metricas, hash integrity)
- `exercise-patterns-frontend`: Vista agregada de como la clase resolvio un ejercicio
- `governance-reports-frontend`: Panel de reportes de governance (violations, prompt history)

### Modified Capabilities
- `cognitive-metrics-api`: Se agrega endpoint de sesiones por comision para permitir navegacion a la traza

## Impact

- **Backend**: Nuevos endpoints en `app/features/cognitive/router.py` y `app/features/governance/router.py`. Nuevo service method en cognitive y governance. NO crea modelos nuevos — consume datos existentes de todas las fases
- **Frontend**: Nuevo feature folder `features/teacher/trace/` con componentes pesados de visualizacion. Nuevo `features/teacher/patterns/` y `features/teacher/governance/`. Nuevas rutas en App.tsx
- **API**: 4 nuevos endpoints GET, todos docente/admin
- **Dependencias**: Consume cognitive_sessions + events (EPIC-13), cognitive_metrics (EPIC-14), tutor_interactions (EPIC-09), code_snapshots (EPIC-08), governance_events (EPIC-11). Todo via REST o query directo al schema propio
- **Cross-schema**: Lee tutor_interactions y code_snapshots del schema operational via sus endpoints REST existentes. Lee cognitive data por query directo (schema propio de Fase 3)
