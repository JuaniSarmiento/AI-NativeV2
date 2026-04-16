## Context

Fases 1 y 2 producen eventos a 3 Redis Streams: events:submissions, events:tutor, events:code. Estos eventos son fire-and-forget — si nadie los consume, se pierden. EPIC-13 los consume, clasifica, y persiste como cognitive events inmutables en una hash chain.

El schema `cognitive` existe pero no tiene tablas. Los modelos estan definidos en la KB.

## Goals / Non-Goals

**Goals:**
- Consumer Redis Streams que procesa eventos de 3 streams con consumer group + ACK
- Cognitive sessions con ciclo de vida (open/closed/invalidated)
- Hash chain SHA-256 inmutable (genesis_hash, event_hash encadenado, session_hash)
- Clasificador que transforma event_type raw → canonico + n4_level
- Endpoints REST para consulta y verificacion de integridad
- Multi-sesion por ejercicio (alumno puede tener N sesiones)

**Non-Goals:**
- Metricas agregadas (EPIC-14)
- Visualizacion del CTR (EPIC-16)
- Risk assessment (EPIC-14)
- Modificar servicios de Fase 1/2

## Decisions

### D1: Consumer como asyncio task en el app lifecycle, no worker separado
El consumer corre como una asyncio task dentro del proceso FastAPI, similar al OutboxWorker. Simplifica deployment — no hay proceso extra. Se inicia en el lifespan del app y se cancela al shutdown.

### D2: Hash chain con SHA-256
- genesis_hash = SHA256("GENESIS:" + session_id + ":" + started_at_iso)
- event_hash(n) = SHA256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso)
- session_hash = ultimo event_hash al cerrar la sesion
- Si la verificacion falla (recalculo no matchea), la sesion se marca invalidated

### D3: Transformacion de event_type raw → canonico
Los nombres del Event Bus NO son los mismos que se almacenan en cognitive_events:
- reads_problem → reads_problem (sin cambio)
- code.executed → code.run
- code.snapshot.captured → code.snapshot
- exercise.submitted → submission.created
- tutor.interaction.completed (role=user) → tutor.question_asked
- tutor.interaction.completed (role=assistant) → tutor.response_received
- tutor.session.started → session.started
- tutor.session.ended → session.closed (tambien cierra la cognitive_session si es la ultima)
- reflection.submitted → reflection.submitted

### D4: Sesion cognitiva lazy — se crea al primer evento
No se crea la sesion al login. Se crea cuando llega el primer evento para un par (student_id, exercise_id) sin sesion open. Tipicamente es reads_problem pero puede ser cualquier evento.

### D5: Cierre por timeout via periodic check
Un asyncio task separado chequea cada 5 minutos las sesiones open cuyo ultimo evento tiene >30 minutos. Las cierra automaticamente. Configurable via settings.

### D6: cognitive_events son INMUTABLES
No hay UPDATE ni DELETE en cognitive_events. Son evidencia. El modelo no tiene updated_at. La tabla no tiene soft delete.

## Risks / Trade-offs

- **[Consumer lag]** → Si el consumer se cae, los eventos se acumulan en Redis (persistidos). Al reconectar, procesa el backlog. ACK garantiza at-least-once.
- **[Hash chain performance]** → Cada evento requiere leer el hash anterior. Mitigacion: cache del ultimo hash por sesion en memoria del consumer.
- **[Concurrencia]** → Dos eventos simultaneos para la misma sesion podrian crear race condition en sequence_number. Mitigacion: UNIQUE constraint + retry, o procesar en orden por sesion.
