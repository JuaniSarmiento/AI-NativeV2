# EPIC-13: Event Classifier y CTR Builder

> **Issue**: #13 | **Milestone**: Fase 3 — Motor Cognitivo | **Labels**: epic, fase-3, priority:critical

**Nivel de gobernanza**: CRITICAL — cambios requieren revisión formal

## Contexto

El Cognitive Trace Record (CTR) es el registro inmutable de todo lo que un alumno hizo durante una sesión de trabajo. Cada evento (ejecutó código, pidió ayuda, cambió estrategia) se clasifica por nivel N4, se encadena con SHA-256 (hash chain), y se agrupa en una sesión cognitiva. El CTR es EVIDENCIA — no se modifica, no se elimina.

Este EPIC es el corazón de Fase 3: consume eventos de Fases 1 y 2 via Event Bus (Redis Streams) y construye el CTR.

## Alcance

### Backend
- Modelos SQLAlchemy: `cognitive_sessions`, `cognitive_events`
- **Event Bus consumer** (Redis Streams con consumer groups — consumer group: `cognitive-group`):
  - Streams consumidos:
    - `events:submissions` — producido por `features/exercises`
    - `events:tutor` — producido por `features/tutor`
    - `events:code` — producido por `features/sandbox`
  - Eventos consumidos:
    - `reads_problem` (de EPIC-06, stream: `events:submissions`) — alumno abre el ejercicio; es el N1 entry point y dispara la creación de sesión
    - `code.executed` (de EPIC-07, stream: `events:code`)
    - `code.execution.failed` (de EPIC-07, stream: `events:code`)
    - `code.snapshot.captured` (de EPIC-08, stream: `events:code`)
    - `exercise.submitted` (de EPIC-08, stream: `events:submissions`)
    - `tutor.session.started` (de EPIC-09, stream: `events:tutor`)
    - `tutor.interaction.completed` (de EPIC-09, stream: `events:tutor`)
    - `tutor.session.ended` (de EPIC-09, stream: `events:tutor`)
    - `reflection.submitted` (de EPIC-12, stream: `events:submissions`)
  - Transforma eventos crudos → cognitive events tipados
  - **IMPORTANTE**: Los nombres de eventos del Event Bus (raw) son DISTINTOS de los `event_type` almacenados en `cognitive_events`. El consumer TRANSFORMA los eventos crudos. Ejemplo: raw `exercise.submitted` del Event Bus → se almacena como `submission.created` en `cognitive_events`.
- **Ciclo de vida de cognitive_session**:
  - **Creada**: cuando llega el primer evento para un par `(student_id, exercise_id)`, típicamente `reads_problem`. Se crea la sesión con `status = open`.
  - **Cerrada**: cuando llega `exercise.submitted` para esa sesión, O después de 30 minutos de inactividad (timeout configurable). `status` cambia a `closed`.
  - **Invalidada**: si la verificación del hash chain falla. `status` cambia a `invalidated`.
  - Un alumno puede tener MÚLTIPLES sesiones por ejercicio (e.g., vuelve al día siguiente = nueva sesión con `status = open`).
- **Cognitive Event Classifier**:
  - Mapea event_type → nivel N4 según catálogo canónico de la KB
  - Catálogo de `cognitive_events.event_type` (valores almacenados en DB):
    - `session.started` — Inicio de sesión (sin nivel N4)
    - `reads_problem` — Leyó el enunciado (N1)
    - `code.snapshot` — Guardó snapshot del código (N1)
    - `tutor.question_asked` — Preguntó al tutor (N4)
    - `tutor.response_received` — El tutor respondió (N4)
    - `code.run` — Ejecutó código en sandbox (N3)
    - `submission.created` — Envió el ejercicio (N2/N3)
    - `reflection.submitted` — Completó reflexión (N1/N2)
    - `session.closed` — Sesión cerrada (sin nivel N4)
- **CTR Builder**:
  - Agrupa eventos por sesión cognitiva (student_id + exercise_id)
  - Hash chain SHA-256: `hash(n) = SHA256(hash(n-1) + datos(n))`
  - `genesis_hash` = SHA256("GENESIS:" + session_id + ":" + started_at) — primer eslabón de la cadena
  - `session_hash` = hash final de toda la sesión al cierre
  - Sequence number auto-incremental por sesión (UNIQUE por session_id)
  - Constraint: `UNIQUE(session_id, sequence_number)` en `cognitive_events`
- **Stream producido**: `events:cognitive` (consumer group: `analytics-group`) — emite `cognitive.classified` y `ctr.entry.created`
- Endpoints:
  - `GET /api/v1/cognitive/sessions/{id}` — detalle de sesión con eventos
  - `GET /api/v1/cognitive/sessions/{id}/verify` — verificar integridad hash chain

### Frontend
- Sin UI propia en esta EPIC (la visualización del CTR está en EPIC-16)

## Contratos

### Produce
- Stream `events:cognitive` → `analytics-group`
  - Eventos: `cognitive.classified`, `ctr.entry.created`, `ctr.hash.verified`
- Modelos `cognitive_sessions`, `cognitive_events` en schema `cognitive`
- Sesiones cognitivas con hash chain verificable (genesis_hash + session_hash)
- Endpoints de consulta de sesiones y verificación
- Datos para EPIC-14 (métricas) y EPIC-16 (traza visual)

### Consume (via Event Bus — Redis Streams)
- `events:submissions` → `reads_problem` (EPIC-06), `exercise.submitted` (EPIC-08), `reflection.submitted` (EPIC-12)
- `events:tutor` → `tutor.session.started`, `tutor.interaction.completed`, `tutor.session.ended` (de EPIC-09)
- `events:code` → `code.executed`, `code.execution.failed` (de EPIC-07), `code.snapshot.captured` (de EPIC-08)

### Modelos (owner — schema: cognitive)

**cognitive_sessions**
- `id` (UUID PK)
- `student_id` (UUID, NOT NULL) — sin FK cross-schema, se valida en service
- `exercise_id` (UUID, NOT NULL) — sin FK cross-schema
- `commission_id` (UUID, NOT NULL) — denormalizado al crear la sesión; tomado del payload del evento `reads_problem` (que incluye `commission_id`) o resuelto via REST `GET /api/v1/exercises/{id}` antes de persistir. Sin FK cross-schema. Permite agregados por comisión en EPIC-14 sin JOINs cross-schema.
- `started_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- `closed_at` (TIMESTAMPTZ, NULLABLE) — NULL = sesión abierta
- `genesis_hash` (VARCHAR 64, NULLABLE) — SHA-256 del hash inicial: SHA256("GENESIS:" + session_id + ":" + started_at)
- `session_hash` (VARCHAR 64, NULLABLE) — SHA-256 hash final de toda la sesión al cierre
- `n4_final_score` (JSONB, NULLABLE) — puntuaciones N1-N4 al cierre
- `status` (ENUM: open/closed/invalidated, NOT NULL, DEFAULT 'open')

**cognitive_events** (INMUTABLE — sin UPDATE ni DELETE, son evidencia)
- `id` (UUID PK)
- `session_id` (UUID FK → cognitive_sessions.id, NOT NULL)
- `event_type` (VARCHAR 100, NOT NULL) — NOT an enum in DB; ver catálogo canónico arriba
- `sequence_number` (INTEGER, NOT NULL)
- `payload` (JSONB, NOT NULL)
- `previous_hash` (VARCHAR 64, NOT NULL) — hash del evento anterior (o genesis_hash)
- `event_hash` (VARCHAR 64, NOT NULL) — SHA-256(previous_hash + event_type + payload + timestamp)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- Constraint: UNIQUE(session_id, sequence_number)

## Dependencias
- **Blocked by**: EPIC-08 (submissions producen eventos), EPIC-09 (tutor produce eventos via `events:tutor`), EPIC-11 (clasificación N4 de interacciones), EPIC-12 (reflexión produce evento `reflection.submitted`)
- **Blocks**: EPIC-14 (métricas se calculan sobre el CTR), EPIC-16 (traza visual muestra el CTR)

## Stories

- [ ] Modelos SQLAlchemy: cognitive_sessions, cognitive_events + migración Alembic
- [ ] Event Bus consumer: Redis Streams consumer group `cognitive-group` sobre `events:submissions`, `events:tutor`, `events:code`
- [ ] Ciclo de vida de sesión: creación al primer evento, cierre por `exercise.submitted` o inactividad 30min, invalidación por hash chain failure
- [ ] Cognitive Event Classifier: mapeo event_type → n4_level (tabla canónica)
- [ ] CTR Builder: agrupación por sesión, hash chain SHA-256 (genesis_hash + event_hash encadenado + session_hash al cierre)
- [ ] Soporte multi-sesión por ejercicio (un alumno puede tener N sesiones abiertas/cerradas para el mismo ejercicio)
- [ ] Producción de eventos al stream `events:cognitive`
- [ ] Endpoints: consulta de sesión + verificación de integridad
- [ ] Tests: hash chain determinismo, integridad, detección de tampering
- [ ] Tests: inmutabilidad (no hay UPDATE/DELETE)
- [ ] Tests: concurrencia (múltiples sesiones simultáneas)
- [ ] Tests: clasificación correcta según mapeo canónico
- [ ] Tests: ciclo de vida de sesión (creación, cierre por submit, cierre por timeout, invalidación)

## Criterio de Done

- Eventos de Fases 1 y 2 se consumen correctamente desde los streams `events:submissions`, `events:tutor`, `events:code`
- Ciclo de vida de sesión funciona: open → closed (por submit o timeout) → invalidated (si hash falla)
- Un alumno puede tener múltiples sesiones por ejercicio
- Cada evento tiene hash SHA-256 encadenado al anterior (previous_hash → event_hash)
- genesis_hash calculado al crear la sesión; session_hash calculado al cerrarla
- Hash chain verificable via endpoint
- Eventos cognitivos se publican al stream `events:cognitive`
- Cognitive events son inmutables
- Tests pasan (incluyendo tests de integridad, tampering, ciclo de vida y concurrencia)

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md` (cognitive schema)
- `knowledge-base/02-arquitectura/05_eventos_y_websocket.md` (Event Bus)
- Mapeo event_type → N4 en features_y_epics.md
