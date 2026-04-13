# EPIC-11: Clasificación N4 y Governance Events

> **Issue**: #11 | **Milestone**: Fase 2 — Tutor IA | **Labels**: epic, fase-2, priority:high

## Contexto

Cada interacción alumno-tutor se clasifica según el modelo N4 (N1-Comprensión, N2-Estrategia, N3-Validación, N4-Interacción IA). Esta clasificación es el INPUT que Fase 3 usa para construir el CTR y calcular métricas. Además, este EPIC registra governance events: violaciones de policy, cambios de prompts, cambios de modelo.

La clasificación N4 la hace Fase 2 porque tiene acceso al CONTEXTO completo de la conversación (prompt, respuesta, estado del código). Fase 3 solo CONSUME la clasificación ya hecha.

**Diseño de la clasificación**: La clasificación ocurre en CADA interacción individualmente. El resultado se persiste directamente como `n4_level` (SMALLINT 1-4) en el registro `tutor_interactions`. No se crea una tabla separada para los resultados de clasificación — el campo en la interacción es la fuente de verdad.

## Alcance

### Backend
- Clasificador N4 de interacciones:
  - Analiza cada turno (mensaje del alumno + respuesta del tutor)
  - Clasifica en: N1 (comprensión), N2 (estrategia), N3 (validación), N4 (interacción IA)
  - Sub-clasificación: critical / exploratory / dependent
  - Persiste `n4_level` (SMALLINT 1-4) en `tutor_interactions` inmediatamente tras clasificar
- Modelo SQLAlchemy: `governance_events`
- Governance service:
  - Registra policy violations (guardrails triggered, desde EPIC-10)
  - Registra prompt updates (nueva versión de system prompt)
  - Registra model changes
  - Registra config changes
- Endpoint: `GET /api/v1/governance/events` (admin only, paginado, filtrable por event_type/severity)
- Versionado de prompts con SHA-256 y audit trail

### Frontend
- Sin UI propia en esta EPIC (la UI de governance está en EPIC-16)
- Los datos se producen para consumo de Fase 3 y EPIC-16

## Contratos

### Produce
- Campo `n4_level` clasificado en cada `tutor_interaction` (SMALLINT 1-4, set por el clasificador)
- Modelo `governance.governance_events`
- Eventos (para Event Bus → Fase 3):
  - `cognitive.classified` (interaction_id, n4_level, sub_classification, exercise_id, student_id)
  - `governance.flag.raised` (event_type, actor_id, target_type, target_id, details)
  - `governance.prompt_updated` (prompt_id, old_hash, new_hash)
- Endpoint de governance events para admin

### Consume
- Interacciones del chat (de EPIC-09) — lee content y contexto para clasificar
- Guardrails results (de EPIC-10) — recibe notificación de violaciones para registrar en governance_events

### Modelos (owner — schema: governance)
- `governance.governance_events`: id (UUID PK), event_type (VARCHAR 100, NOT NULL), actor_id (UUID, NOT NULL), target_type (VARCHAR 100, NULLABLE), target_id (UUID, NULLABLE), details (JSONB, NOT NULL), created_at (TIMESTAMPTZ)

  **Tipos de event_type (catálogo)**: `prompt.created`, `prompt.activated`, `prompt.deactivated`, `guardrail.triggered`, `guardrail.overridden`, `course.created`, `enrollment.bulk_created`

  **Nota**: `event_type` es VARCHAR(100), no un enum a nivel de DB — los tipos son convenciones de aplicación, no constraints de base de datos.

## Dependencias
- **Blocked by**: EPIC-09, EPIC-10 (necesita interacciones y guardrails)
- **Blocks**: EPIC-13 (CTR consume clasificación N4), EPIC-16 (UI de traza usa clasificación)

## Stories

- [ ] Clasificador N4: analizar turno y asignar nivel (1/2/3/4 como SMALLINT)
- [ ] Sub-clasificación: critical / exploratory / dependent
- [ ] Persistir n4_level en tutor_interactions (SMALLINT 1-4)
- [ ] Modelo SQLAlchemy: governance_events + migración
- [ ] GovernanceService: registrar violations, prompt updates, model changes, config changes
- [ ] Endpoint `GET /api/v1/governance/events` (admin, paginado, filtrable)
- [ ] Producir eventos para Event Bus (`cognitive.classified`, `governance.flag.raised`, `governance.prompt_updated`)
- [ ] Tests: clasificación correcta para distintos tipos de interacción
- [ ] Tests: governance events se registran correctamente con event_type, actor_id, target_type, target_id

## Criterio de Done

- Cada interacción alumno-tutor tiene clasificación N4 como SMALLINT 1-4
- `governance_events` usa VARCHAR(100) para event_type (no enum de DB)
- `governance_events` tiene `actor_id (UUID, NOT NULL)`, `target_type (VARCHAR 100, NULLABLE)`, `target_id (UUID, NULLABLE)`
- `governance_events` NO tiene campo `severity`
- Governance events se registran automáticamente
- Eventos emitidos al Event Bus con nombres canónicos (`cognitive.classified`, `governance.flag.raised`)
- Admin puede consultar governance events
- Tests pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md` (governance schema)
- `rubrics/n4_anexo_b.yaml`
- Mapeo event_type → N4 del documento maestro (empate3)
