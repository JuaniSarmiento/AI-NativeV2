# EPIC-09: Chat Streaming con Tutor IA

> **Issue**: #9 | **Milestone**: Fase 2 — Tutor IA | **Labels**: epic, fase-2, priority:critical

## Contexto

El corazón de la Fase 2: un chat en tiempo real entre el alumno y el tutor IA socrático. El tutor guía sin dar respuestas, usa streaming token-por-token via WebSocket, y cada interacción se registra con clasificación N4 y hash del prompt vigente.

**Nota de alcance**: Este EPIC implementa el chat con un system prompt básico hardcodeado (placeholder socrático funcional). El `ContextBuilder` completo (que incorpora ejercicio + código + historial + constraints) y el `GuardrailsProcessor` se implementan en EPIC-10, que reemplaza el placeholder. Esto permite que EPIC-09 entregue un chat funcionando sin bloquear a EPIC-10.

## Alcance

### Backend
- Modelos SQLAlchemy: `tutor_interactions`, `tutor_system_prompts`
- WebSocket endpoint: `ws://api/ws/tutor/chat?token=<JWT>`
  - Autenticación JWT via query param en handshake
  - Streaming de tokens del LLM al frontend
  - Heartbeat ping/pong para detección de desconexión
- Cliente LLM (Anthropic adapter):
  - Streaming response
  - Token counting
  - Error handling (rate limits, API errors)
  - Configurable por modelo (haiku en dev, sonnet en prod)
- Rate limiting: 30 msg/hora por alumno POR EJERCICIO
- System prompt básico hardcodeado como punto de partida (EPIC-10 lo reemplaza)

### Frontend
- Componente `TutorChat`:
  - Chat con mensajes alumno/tutor
  - Streaming de texto progresivo (token por token)
  - Indicador "el tutor está escribiendo..."
  - Historial de conversación de la sesión actual
  - Input con enviar (Enter) y multiline (Shift+Enter)
- WebSocket connection management:
  - Ref pattern con dos `useEffect`s separados
  - Reconexión con exponential backoff
  - Cleanup en unmount
- Actualización del store via actions, NUNCA setState directo

## Contratos

### Produce
- WebSocket endpoint `/ws/tutor/chat`
- Modelo `tutor_interactions` en schema `operational`
- Modelo `tutor_system_prompts` en schema `governance`
- Eventos (stream: `events:tutor`, para Event Bus → Fase 3):
  - `tutor.interaction.completed` (student_id, exercise_id, role, n4_classification, prompt_hash)
  - `tutor.session.started` (student_id, exercise_id, timestamp)
  - `tutor.session.ended` (student_id, exercise_id, message_count, timestamp)
- `LLMAdapter` interface (para futuro soporte multi-modelo)

### Consume
- Auth JWT (de EPIC-03) — validación en WS handshake
- Ejercicios (de EPIC-06) — contexto del ejercicio actual
- Submissions/Code actual (de EPIC-08) — código que el alumno está escribiendo
- Redis para rate limiting (de EPIC-01)

### Modelos (owner — schema: operational)
- `operational.tutor_interactions`: id (UUID PK), session_id (UUID, NOT NULL — correlación lógica con cognitive_sessions.id, sin FK cross-schema), student_id (FK → users), exercise_id (FK → exercises), role (ENUM user/assistant), content (TEXT), n4_level (SMALLINT nullable, CHECK (n4_level BETWEEN 1 AND 4)), tokens_used (INTEGER nullable), model_version (VARCHAR 100 nullable), prompt_hash (VARCHAR 64 NOT NULL), created_at (TIMESTAMPTZ)

### Modelos (owner — schema: governance)
- `governance.tutor_system_prompts`: id (UUID PK), name (VARCHAR), content (TEXT), sha256_hash (VARCHAR 64), version (VARCHAR 50, NOT NULL), is_active (BOOL), guardrails_config (JSONB), created_by (UUID, NOT NULL) -- ID del admin que creó el prompt (sin FK cross-schema, se valida en service layer), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ, NOT NULL)

## Dependencias
- **Blocked by**: EPIC-03 (auth), EPIC-06 (ejercicios), EPIC-08 (código actual del alumno)
- **Blocks**: EPIC-10 (guardrails procesan la respuesta del chat), EPIC-11 (clasificación N4 de cada turno), EPIC-13 (CTR consume eventos del tutor via `events:tutor`), EPIC-16 (traza visual consume tutor_interactions)

## Stories

- [ ] Modelos SQLAlchemy: tutor_interactions, tutor_system_prompts + migraciones
- [ ] WebSocket endpoint con auth JWT via query param
- [ ] Cliente LLM: Anthropic adapter con streaming
- [ ] Streaming de tokens via WebSocket al frontend
- [ ] Heartbeat ping/pong para detección de desconexión
- [ ] Rate limiting: 30 msg/hora por alumno por ejercicio (Redis)
- [ ] Registro de cada interacción (content, tokens, model, prompt_hash)
- [ ] System prompt básico hardcodeado (placeholder socrático funcional)
- [ ] Frontend: componente TutorChat con streaming progresivo
- [ ] Frontend: indicador "escribiendo...", historial de sesión
- [ ] Frontend: WebSocket con ref pattern, reconexión exponential backoff
- [ ] Frontend: integración en vista de ejercicio (panel derecho)
- [ ] Producir eventos para Event Bus
- [ ] Tests: WebSocket connection, streaming, rate limiting, reconnection

## Criterio de Done

- Alumno puede chatear con el tutor en tiempo real con streaming
- Auth JWT funciona en WS handshake
- Rate limiting activo (30 msg/hora por ejercicio)
- Cada interacción registrada con prompt_hash SHA-256
- `tutor_interactions` tiene `session_id` (correlación lógica, sin FK cross-schema) pero NO tiene `policy_check_result` (violaciones van a governance_events)
- `n4_level` es SMALLINT nullable con CHECK (1-4), no un enum de strings
- Reconexión automática ante desconexión
- Tests pasan

## Referencia
- `knowledge-base/02-arquitectura/05_eventos_y_websocket.md`
- `knowledge-base/01-negocio/05_flujos_principales.md`
- `prompts/socratic_tutor_system.md`
