## Why

El CTR (Cognitive Trace Record) es el registro inmutable de todo el proceso cognitivo del alumno. Sin el, no hay evaluacion basada en el modelo N4 — solo hay eventos sueltos en Redis Streams sin persistencia ni encadenamiento. EPIC-13 es el corazon de Fase 3: consume eventos de Fases 1 y 2, los clasifica por nivel N4, los agrupa en sesiones cognitivas, y los encadena con SHA-256 para garantizar inmutabilidad.

## What Changes

- Modelos SQLAlchemy: `cognitive_sessions` y `cognitive_events` en schema cognitive
- Event Bus consumer (Redis Streams consumer group `cognitive-group`) que consume de 3 streams
- Cognitive Event Classifier: mapea event_type raw → event_type canonico + n4_level
- CTR Builder: agrupa por sesion, hash chain SHA-256 (genesis + encadenado + session_hash)
- Ciclo de vida de sesion: open → closed (por submit/timeout) → invalidated (hash failure)
- Endpoints: GET sesion con eventos, GET verificacion hash chain
- Produccion de eventos al stream `events:cognitive`

## Capabilities

### New Capabilities
- `cognitive-session-model`: Modelos cognitive_sessions y cognitive_events con migration
- `event-bus-consumer`: Redis Streams consumer con consumer group cognitive-group
- `cognitive-event-classifier`: Mapeo de eventos raw a event_types canonicos con nivel N4
- `ctr-builder`: Hash chain SHA-256, agrupacion por sesion, genesis/session hash
- `cognitive-session-lifecycle`: Creacion, cierre por submit/timeout, invalidacion
- `cognitive-api`: Endpoints de consulta de sesion y verificacion de integridad

### Modified Capabilities
- Ninguna — EPIC-13 es consumer puro, no modifica servicios existentes

## Impact

- Backend: nuevo modulo `app/features/cognitive/` completo
- Migration: 2 tablas en schema cognitive
- Redis: nuevo consumer group `cognitive-group` sobre 3 streams
- Sin cambios en frontend (UI del CTR es EPIC-16)
- Sin cambios en Fases 1/2 — EPIC-13 solo consume
