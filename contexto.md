# Contexto de Contratos — EPICs 01-13

> Resumen de todo lo implementado hasta ahora para que la próxima sesión no tenga que leer 50 archivos.
> Última actualización: 2026-04-15 (post-apply EPIC-13)

---

## Estado General

EPICs 01-13 implementadas y archivadas. EPIC-14 es la siguiente.

| EPIC | Fase | Estado |
|------|------|--------|
| 01 — Infra y DevOps | 0 | Archivada |
| 02 — Base de Datos | 0 | Archivada |
| 03 — Auth JWT + RBAC | 0 | Archivada |
| 04 — Contratos + MSW + Design System | 0 | Archivada |
| 05 — Cursos y Comisiones | 1 | Archivada |
| 06 — Ejercicios | 1 | Archivada |
| 06b — Actividades IA + RAG | 1 | Archivada |
| 07 — Sandbox Ejecución | 1 | Archivada |
| 08 — Submissions + Snapshots | 1 | Archivada |
| 09 — Chat Streaming Tutor | 2 | Archivada |
| 10 — Prompt Engine + Guardrails | 2 | Archivada |
| 11 — N4 Classifier + Governance | 2 | Archivada |
| 12 — Reflexión Post-Ejercicio | 2 | Archivada |
| 13 — Event Classifier + CTR Builder | 3 | Archivada |
| **14 — Cognitive Metrics Engine** | **3** | **Siguiente** |

---

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 (4 schemas) + Redis 7
- **Frontend**: React 19 + TypeScript + Zustand 5 + TailwindCSS 4 + Vite
- **LLM**: Mistral (mistralai v2.3.2) — config switcheable con `TUTOR_LLM_PROVIDER`
- **Docker**: docker-compose en `devOps/`, volumes montan backend/ y frontend/ con hot reload

---

## Arquitectura Backend

```
Router (thin — HTTP/WS only)
  → Domain Service (lógica, validación, orquestación)
    → Repository (queries, extiende BaseRepository)
      → Model (SQLAlchemy, por schema)
```

- **UoW**: `AsyncUnitOfWork` en `app/shared/db/unit_of_work.py` — repos nunca commitean
- **Session**: `get_async_session()` yields per-request, `expire_on_commit=False`
- **Exceptions**: `DomainError` → `NotFoundError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`, `ConflictError`
- **Response format**: `{ status, data, meta, errors }`
- **Logging**: `get_logger(__name__)`, NUNCA print()

---

## Schemas PostgreSQL

| Schema | Owner | Tablas |
|--------|-------|--------|
| operational | Fases 0-2 | users, courses, commissions, enrollments, exercises, activities, submissions, activity_submissions, code_snapshots, tutor_interactions, event_outbox |
| governance | Fase 2 | tutor_system_prompts, governance_events (EPIC-11) |
| cognitive | Fase 3 | cognitive_sessions, cognitive_events (EPIC-13) |
| analytics | Fase 3 | cognitive_metrics, reasoning_records (EPIC-14) |

---

## Modelos Relevantes para EPIC-10

### `operational.tutor_interactions` (EPIC-09)
Owner del schema. Cada turno alumno/tutor.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID PK | |
| session_id | UUID NOT NULL | Correlación lógica con cognitive_sessions, sin FK cross-schema |
| student_id | UUID FK → users | |
| exercise_id | UUID FK → exercises | |
| role | ENUM user/assistant | |
| content | TEXT | |
| n4_level | SMALLINT nullable | CHECK 1-4, seteado por EPIC-11 classifier |
| tokens_used | INTEGER nullable | |
| model_version | VARCHAR 100 | |
| prompt_hash | VARCHAR 64 NOT NULL | SHA-256 del system prompt activo |
| created_at | TIMESTAMPTZ | |

### `governance.tutor_system_prompts` (EPIC-09)
Prompts versionados con SHA-256.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR 255 | |
| content | TEXT | |
| sha256_hash | VARCHAR 64 UNIQUE | Auto-computed |
| version | VARCHAR 50 | |
| is_active | BOOL | Solo 1 activo a la vez (no enforceado aún) |
| guardrails_config | JSONB nullable | Para config de guardrails |
| created_by | UUID | Sin FK cross-schema |
| created_at / updated_at | TIMESTAMPTZ | |

Tiene `compute_hash(content)` static method.

### `operational.exercises` (EPIC-06)
Ejercicios con enunciado, test cases, rubric.

| Campo clave | Tipo | Notas |
|-------------|------|-------|
| id | UUID | |
| course_id | UUID FK → courses | Ejercicios pertenecen a CURSOS, no comisiones |
| title | VARCHAR 255 | |
| description | TEXT | El enunciado que el ContextBuilder necesita |
| test_cases | JSONB | `{ language, timeout_ms, memory_limit_mb, cases: [...] }` |
| difficulty | ENUM easy/medium/hard | |
| topic_tags | TEXT[] | |
| starter_code | TEXT | |
| rubric | TEXT nullable | Rúbrica para AI grading |
| language | VARCHAR 50 | Default "python" |

### `operational.code_snapshots` (EPIC-08)
Snapshots inmutables del código del alumno.

| Campo | Tipo |
|-------|------|
| id | UUID |
| student_id | UUID |
| exercise_id | UUID |
| code | TEXT |
| snapshot_at | TIMESTAMPTZ |

---

## Auth

- JWT access (15min) + refresh (7d) con rotation
- `get_current_user()` y `require_role()` en `app/features/auth/dependencies.py`
- `CurrentUser` = `Annotated[User, Depends(get_current_user)]`
- Para roles: `_user=require_role("alumno")` como param SEPARADO (NO como default de CurrentUser)
- WS auth: `validate_ws_token(token, redis)` en `app/core/security.py`
- Redis blacklist: `auth:blacklist:{jti}`
- Roles: alumno, docente, admin

---

## Event Bus

4 Redis Streams: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`

### Outbox Pattern
Eventos se escriben a `event_outbox` en la misma TX de DB. `OutboxWorker` los publica a Redis Streams.

**Routing** (`app/core/outbox_worker.py` → `_STREAM_ROUTING`):

| Prefix del event_type | Stream |
|----------------------|--------|
| `submission` | events:submissions |
| `reads` | events:submissions |
| `reflection` | events:submissions |
| `exercise` | events:submissions |
| `tutor` | events:tutor |
| `guardrail` | events:tutor |
| `governance` | events:tutor |
| `code` | events:code |
| `cognitive` | events:cognitive |

**GAP `reads_problem` ARREGLADO** en esta sesión (EPIC-13).

### Eventos producidos hasta ahora

| Evento | Productor | Stream | Payload clave |
|--------|-----------|--------|---------------|
| `reads_problem` | EPIC-06 | events:submissions* | student_id, exercise_id, course_id |
| `code.executed` | EPIC-07 | events:code | student_id, exercise_id, status, runtime_ms |
| `code.execution.failed` | EPIC-07 | events:code | student_id, exercise_id, error |
| `code.snapshot.captured` | EPIC-08 | events:code | student_id, exercise_id, snapshot_id |
| `exercise.submitted` | EPIC-08 | events:submissions | student_id, exercise_id, submission_id |
| `tutor.session.started` | EPIC-09 | events:tutor | student_id, exercise_id, session_id |
| `tutor.interaction.completed` | EPIC-09 | events:tutor | interaction_id, student_id, exercise_id, session_id, role, n4_classification, prompt_hash, tokens_used |
| `tutor.session.ended` | EPIC-09 | events:tutor | student_id, exercise_id, session_id, message_count |

Nuevos eventos (EPICs 10-13):

| Evento | Productor | Stream | Payload clave |
|--------|-----------|--------|---------------|
| `guardrail.triggered` | EPIC-10 | events:tutor | interaction_id, student_id, exercise_id, violation_type, violation_details |
| `cognitive.classified` | EPIC-11 | events:cognitive | interaction_id, n4_level, sub_classification, student_id, exercise_id |
| `governance.flag.raised` | EPIC-11 | events:tutor | event_type, actor_id, target_type, details |
| `reflection.submitted` | EPIC-12 | events:submissions | student_id, reflection_id, activity_submission_id, difficulty_perception, confidence_level |

---

## Tutor Chat (EPIC-09) — Lo que ya existe

### Backend (`app/features/tutor/`)

| Archivo | Qué hace |
|---------|----------|
| `models.py` | TutorInteraction + TutorSystemPrompt |
| `llm_adapter.py` | LLMAdapter ABC, AnthropicAdapter, **MistralAdapter** (activo) |
| `rate_limiter.py` | Redis sliding window, 30 msg/hora/ejercicio |
| `schemas.py` | WS discriminated union (chat.message, ping → chat.token, chat.done, chat.error, rate_limit, pong) |
| `repositories.py` | TutorInteractionRepository, TutorPromptRepository |
| `service.py` | TutorService — orquesta rate limit → prompt → LLM → persist → outbox |
| `router.py` | WS `/ws/tutor/chat` + REST GET `/api/v1/tutor/sessions/{exercise_id}/messages` |
| `seed.py` | Prompt socrático básico v1 |

### Flujo actual del chat (simplificado)

```
1. Alumno envía mensaje via WS
2. Router valida auth + rate limit
3. TutorService:
   a. Carga prompt activo (TutorPromptRepository.get_active_prompt())
   b. Carga historial (últimos 20 mensajes de la sesión)
   c. Llama LLM con: system_prompt + historial + mensaje nuevo
   d. Streaming: yield tokens → WS → frontend
   e. Persiste user turn + assistant turn en tutor_interactions
   f. Escribe outbox event tutor.interaction.completed
```

### ⚠ Lo que FALTA (para EPIC-10)

El TutorService hoy hace esto en `_get_active_prompt()`:
```python
async def _get_active_prompt(self) -> TutorSystemPrompt:
    if self._active_prompt is None:
        self._active_prompt = await self._prompt_repo.get_active_prompt()
    return self._active_prompt
```

Solo devuelve el system prompt raw. NO tiene:
- Contexto del ejercicio (enunciado, dificultad, topics)
- Código actual del alumno
- Constraints específicos del ejercicio
- Post-procesamiento de guardrails

EPIC-10 debe:
1. Crear `ContextBuilder` que arme el prompt completo con todo el contexto
2. Crear `GuardrailsProcessor` que analice cada respuesta ANTES de enviarla
3. Integrar ambos en el flujo de `TutorService.chat()`

### Frontend (`src/features/tutor/`)

| Archivo | Qué hace |
|---------|----------|
| `store.ts` | `useTutorStore` — messages, connectionStatus, isStreaming, remainingMessages |
| `hooks/useWebSocketTutor.ts` | WS ref pattern, 2 useEffects, exponential backoff, heartbeat 30s |
| `components/TutorChat.tsx` | Chat completo con Card double-bezel, status dot, rate limit |
| `components/ChatMessage.tsx` | Burbujas minimalistas, streaming cursor |

Integrado en `src/features/activities/StudentActivityViewPage.tsx` (panel derecho desktop, bottom sheet mobile).

**⚠ IMPORTANTE**: El tutor está en `StudentActivityViewPage`, NO en `ExerciseDetailPage`. Los alumnos trabajan desde actividades.

---

## Design System (frontend)

- Card: double-bezel (outer ring + inner elevated surface)
- Button: spring easing `cubic-bezier(0.32,0.72,0,1)`, `active:scale-[0.98]`
- Input: border con theme tokens, focus ring sutil
- Colors: CSS custom properties (`--color-neutral-*`, `--color-text-*`, `--color-surface`, `--color-border`)
- Dark mode: `dark:` variant
- Responsive: mobile-first con `sm:`, `md:`, `lg:`
- NUNCA hex hardcodeados, NUNCA console.*, NUNCA gradientes

---

## Config LLM (`app/config.py`)

```python
# Anthropic
anthropic_api_key, anthropic_model, anthropic_max_tokens, anthropic_timeout_seconds

# Mistral (activo)
mistral_api_key, mistral_model ("mistral-small-latest"), mistral_max_tokens (1024)

# Tutor
tutor_llm_provider ("mistral" | "anthropic")
tutor_rate_limit_per_hour (30)
```

Factory en router: `_create_llm_adapter()` devuelve MistralAdapter o AnthropicAdapter según config.

---

## Gotchas conocidos

1. **mistralai v2.3.2**: import es `from mistralai.client import Mistral`, NO `from mistralai import Mistral`
2. **CurrentUser + require_role**: NUNCA `current_user: CurrentUser = require_role(...)`. Usar `_user=require_role(...)` como param separado
3. **Docker .env**: espacios al inicio de las líneas se ignoran silenciosamente
4. **Prompt activo**: v2 activo (`socratic_tutor_contextual_v2`), v1 desactivado. Seed desactiva anteriores.
5. **Reconnect WS**: el frontend NO carga historial via REST al reconectar (warning del verify)
6. ~~**reads_problem routing**~~: ARREGLADO — prefix `reads` agregado a `_STREAM_ROUTING`
7. **SQLAlchemy Enum + Alembic**: cognitive_sessions.status usa VARCHAR(20), NO PostgreSQL ENUM. El SAEnum causaba DuplicateObjectError al migrar. Arreglado usando String(20) en modelo y migration.
8. **Test helpers SQLAlchemy**: usar `MagicMock(spec=Model)` para crear objetos fake, NO `Model.__new__()` que falla por instrumentación de mapped attributes.
9. **N4Classifier regex typo**: "ag reg" fue corregido a "agreg" en EPIC-11 verify.
10. **rate_limiter tests**: 2 tests pre-existentes fallan en test_rate_limiter.py (no relacionados con EPICs 10-13)
11. **Consumer Redis**: usa `decode_responses=False` para bytes crudos de XREADGROUP. El EventBus wrappea payloads en campo `data` JSON string.

---

## Para EPIC-10 específicamente

### Qué crear
- `ContextBuilder` service en `app/features/tutor/context_builder.py`
- `GuardrailsProcessor` service en `app/features/tutor/guardrails.py`
- System prompt socrático v2 (basado en Anexo A del documento maestro)
- Integración en el flujo de `TutorService.chat()`

### Qué consumir
- `Exercise` model (exercise_id → enunciado, dificultad, topics, rubric, starter_code)
- `CodeSnapshot` model (último snapshot del alumno para ese ejercicio)
- `TutorInteraction` model (historial de la sesión)
- `TutorSystemPrompt` model (prompt activo con guardrails_config)

### Qué producir
- Evento `guardrail.triggered` al outbox (para Event Bus)
- Datos para `governance_events` (que EPIC-11 persiste)
- NO crear modelos nuevos — usar los existentes

### Dónde integrarse
Modificar `TutorService.chat()` en `app/features/tutor/service.py`:
- Antes de llamar al LLM: usar ContextBuilder para armar el prompt completo
- Después de cada token stream: usar GuardrailsProcessor para validar la respuesta completa
- Si guardrail triggered: reformular y enviar la versión reformulada

### Tests críticos
- 20+ tests adversarios (jailbreak, pedir solución directa, pedir código completo)
- Tests de ContextBuilder con distintos estados (sin código, con código, con historial largo)

---

## EPIC-10 — Prompt Engine + Guardrails (IMPLEMENTADA)

### Archivos creados/modificados
| Archivo | Qué hace |
|---------|----------|
| `tutor/context_builder.py` | ContextBuilder — compone prompt con ejercicio + rubrica + codigo alumno + actividad |
| `tutor/guardrails.py` | GuardrailsProcessor — detecta codigo excesivo (>5 lineas), soluciones directas, respuestas no-socraticas |
| `tutor/n4_classifier.py` | N4Classifier — clasifica por nivel cognitivo (EPIC-11) |
| `tutor/service.py` | Integra ContextBuilder (pre-LLM) + GuardrailsProcessor (post-stream) + N4Classifier |
| `tutor/seed.py` | Prompt v2 con placeholders dinámicos, desactiva v1 |
| `tutor/schemas.py` | ChatGuardrailOut para mensaje de corrección |
| `tutor/router.py` | Envía ChatGuardrailOut + catch NotFoundError |

### Pipeline del chat actualizado
```
mensaje → rate limit → ContextBuilder(ejercicio+rubrica+codigo) → LLM stream
→ GuardrailsProcessor → N4Classifier(user+assistant) → persist(con n4_level)
→ outbox(cognitive.classified × 2 + guardrail si aplica + governance event)
```

### Prompt v2 activo
`socratic_tutor_contextual_v2` con placeholders: `{exercise_title}`, `{exercise_description}`, `{exercise_difficulty}`, `{exercise_topics}`, `{exercise_language}`, `{exercise_rubric}`, `{student_code}`, `{activity_title}`, `{activity_description}`. Rubrica/actividad se stripean si no existen.

### Guardrails config
`guardrails_config: {"max_code_lines": 5}` en TutorSystemPrompt.guardrails_config JSONB. Configurable sin redeploy.

### Frontend
- `tutor/types.ts`: GuardrailViolationType, chat.guardrail en WSIncoming
- `tutor/hooks/useWebSocketTutor.ts`: case chat.guardrail → addMessage con isGuardrail
- `tutor/components/ChatMessage.tsx`: burbuja guardrail con borde amber, "Nota pedagogica"

---

## EPIC-11 — N4 Classifier + Governance Events (IMPLEMENTADA)

### Archivos creados/modificados
| Archivo | Qué hace |
|---------|----------|
| `tutor/n4_classifier.py` | Regex patterns N4→N3→N2→N1 para user y assistant. Sub-clasificación: critical/dependent/exploratory |
| `governance/models.py` | GovernanceEvent: event_type VARCHAR(100), actor_id, target_type/id, details JSONB |
| `governance/service.py` | record_event, record_guardrail_violation, record_prompt_created/activated/deactivated |
| `governance/repositories.py` | list_events con paginación + filtro por event_type |
| `governance/router.py` | GET /api/v1/governance/events (admin only) |
| `governance/schemas.py` | GovernanceEventResponse, GovernanceEventsListResponse |
| `alembic/versions/010_*.py` | Migration governance_events |

### N4 Classification
- N1 (comprensión): "no entiendo", "que tengo que hacer"
- N2 (estrategia): "como hago para", "deberia usar"
- N3 (validación): "por que da error", "no funciona"
- N4 (interacción IA): "esta bien mi solucion", "que opinas"
- Default: N1. Sub: critical (trabado) / dependent (confirma todo) / exploratory (default)

### Governance event_types
`prompt.created`, `prompt.activated`, `prompt.deactivated`, `guardrail.triggered`, `course.created`, `enrollment.bulk_created`

---

## EPIC-12 — Reflexión Post-Ejercicio (IMPLEMENTADA)

### Archivos creados/modificados
| Archivo | Qué hace |
|---------|----------|
| `submissions/models.py` | Reflection model: activity_submission_id UNIQUE FK, difficulty_perception 1-5, strategy_description, ai_usage_evaluation, what_would_change, confidence_level 1-5 |
| `submissions/services.py` | ReflectionService: create_reflection (validación ownership + unicidad), get_reflection |
| `submissions/schemas.py` | CreateReflectionRequest, ReflectionResponse |
| `submissions/router.py` | POST + GET /api/v1/submissions/{id}/reflection |
| `alembic/versions/011_*.py` | Migration reflections table |
| `frontend/submissions/ReflectionForm.tsx` | Formulario guiado 5 campos, validación, skip link |
| `frontend/submissions/ReflectionView.tsx` | Vista read-only con Card pattern |
| `frontend/activities/StudentActivityViewPage.tsx` | Integración: submit → ReflectionForm → confirmación |

### Flujo frontend
1. Alumno envía actividad → aparece ReflectionForm (no redirect inmediato)
2. Llena los 5 campos (o skip) → confirmación "Actividad enviada"
3. Si revisita → ReflectionView read-only

---

## EPIC-13 — Event Classifier + CTR Builder (IMPLEMENTADA)

### Archivos creados/modificados
| Archivo | Qué hace |
|---------|----------|
| `cognitive/models.py` | CognitiveSession (student_id, exercise_id, commission_id, genesis_hash, session_hash, status open/closed/invalidated) + CognitiveEvent (session_id FK, event_type, sequence_number, payload, previous_hash, event_hash) — INMUTABLE |
| `cognitive/classifier.py` | CognitiveEventClassifier: mapea raw → canónico + N4 level |
| `cognitive/ctr_builder.py` | compute_genesis_hash, compute_event_hash, verify_chain |
| `cognitive/service.py` | CognitiveService: get_or_create_session, add_event (hash chain), close_session, verify_session |
| `cognitive/repositories.py` | CognitiveSessionRepo (get_open_session, get_stale_sessions), CognitiveEventRepo (get_last_event) |
| `cognitive/consumer.py` | CognitiveEventConsumer: XREADGROUP sobre 3 streams, consumer group cognitive-group |
| `cognitive/router.py` | GET /api/v1/cognitive/sessions/{id} + GET .../verify |
| `cognitive/schemas.py` | CognitiveSessionResponse, CognitiveEventResponse, VerifyResponse |
| `alembic/versions/012_*.py` | Migration cognitive_sessions + cognitive_events |

### Transformación de eventos raw → canónicos
| Raw (Event Bus) | Canónico (CTR) | N4 |
|-----------------|----------------|----|
| reads_problem | reads_problem | N1 |
| code.snapshot.captured | code.snapshot | N1 |
| code.executed | code.run | N3 |
| code.execution.failed | code.run | N3 |
| exercise.submitted | submission.created | N2 |
| tutor.interaction.completed (user) | tutor.question_asked | N4 |
| tutor.interaction.completed (assistant) | tutor.response_received | N4 |
| tutor.session.started | session.started | — |
| tutor.session.ended | session.closed | — |
| reflection.submitted | reflection.submitted | N1 |

### Hash chain SHA-256
- genesis_hash = SHA256("GENESIS:" + session_id + ":" + started_at_iso)
- event_hash(n) = SHA256(previous_hash + ":" + event_type + ":" + sorted_json(payload) + ":" + timestamp_iso)
- session_hash = último event_hash al cerrar
- Verificable via endpoint GET /api/v1/cognitive/sessions/{id}/verify

### Ciclo de vida de sesión
- **Creación**: al primer evento para (student_id, exercise_id) sin sesión open
- **Cierre**: por exercise.submitted o timeout 30 min de inactividad
- **Invalidación**: si verify_chain detecta hash mismatch

### Consumer Redis Streams
- Consumer group: `cognitive-group`
- Streams: events:submissions, events:tutor, events:code
- Corre como asyncio task en app lifespan
- Timeout checker cada 5 min cierra sesiones inactivas

---

## Para EPIC-14 específicamente

### Qué crear
- `CognitiveMetrics` model en schema cognitive (n1-n4 scores, qe, dependency, reflection_score, risk_level)
- `CognitiveMetricsWorker` que calcula métricas al cierre de sesión
- `RiskAssessment` model en schema analytics
- `EvaluationEngine` con función E = f(N1, N2, N3, N4, Qe)

### Qué consumir
- `cognitive_sessions` (cerradas) con sus `cognitive_events`
- `reflections` (para reflection_score)
- Clasificaciones N4 de los eventos

### Qué producir
- Métricas agregadas por sesión
- Risk assessments por alumno
- Datos para dashboard docente (EPIC-16)

### Referencia
- `epics/EPIC-14.md`
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md` (analytics schema)
