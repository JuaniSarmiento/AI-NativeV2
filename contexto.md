# Contexto de Contratos — EPICs 01-10

> Resumen de todo lo implementado hasta ahora para que la próxima sesión no tenga que leer 50 archivos.
> Última actualización: 2026-04-14 (post-apply EPIC-10)

---

## Estado General

EPICs 01-10 implementadas. EPIC-10 aplicada, pendiente de verify+archive.

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
| **10 — Prompt Engine + Guardrails** | **2** | **Aplicada** |

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
| `tutor` | events:tutor |
| `code` | events:code |
| `cognitive` | events:cognitive |

**⚠ GAP conocido**: `reads_problem` tiene prefix `reads` que NO matchea ningún routing. Arreglar antes de EPIC-13.

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

*reads_problem tiene bug de routing — ver GAP arriba.

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
4. **Prompt activo**: solo hay 1 prompt seeded (`socratic_tutor_basic_v1`). No hay lógica para desactivar los otros al activar uno nuevo
5. **Reconnect WS**: el frontend NO carga historial via REST al reconectar (warning del verify)
6. **reads_problem routing**: el outbox worker no routea este evento correctamente (prefix `reads` no existe en `_STREAM_ROUTING`)

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
