## Why

El tutor IA socrático es el componente central de Fase 2. Sin él, no hay interacción pedagógica, no hay eventos para el CTR (Fase 3), y no hay datos para el motor cognitivo. EPIC-09 entrega el chat streaming en tiempo real entre alumno y tutor, con registro de cada interacción incluyendo clasificación N4 y hash del prompt vigente. Usa un system prompt básico hardcodeado — EPIC-10 lo reemplaza con ContextBuilder y guardrails completos.

## What Changes

- Nuevo WebSocket endpoint `ws://api/ws/tutor/chat?token=<JWT>` con auth en handshake
- Nuevo modelo `tutor_interactions` (schema: operational) — registro de cada turno alumno/tutor con `session_id`, `n4_level`, `prompt_hash`, `tokens_used`, `model_version`
- Nuevo modelo `tutor_system_prompts` (schema: governance) — versionado de prompts con SHA-256
- Cliente LLM: Anthropic adapter con streaming, token counting, error handling
- Rate limiting: 30 msg/hora por alumno por ejercicio (Redis)
- Producción de eventos al Event Bus: `tutor.interaction.completed`, `tutor.session.started`, `tutor.session.ended` → stream `events:tutor`
- Frontend: componente `TutorChat` con streaming token-por-token, indicador "escribiendo...", reconexión con exponential backoff, ref pattern con dos useEffects
- Heartbeat ping/pong para detección de desconexión

## Capabilities

### New Capabilities
- `tutor-chat-ws`: WebSocket endpoint para chat streaming alumno-tutor, incluyendo auth JWT en handshake, heartbeat, y rate limiting
- `tutor-models`: Modelos SQLAlchemy para `tutor_interactions` y `tutor_system_prompts` con migraciones Alembic
- `tutor-llm-adapter`: Cliente Anthropic con streaming, token counting, y error handling configurable por modelo
- `tutor-chat-frontend`: Componente TutorChat con streaming progresivo, WebSocket management, y store Zustand
- `tutor-events`: Producción de eventos del tutor al Event Bus (`events:tutor` stream)

### Modified Capabilities
- `event-bus-core`: Agregar routing de eventos `tutor.*` al stream `events:tutor` en la tabla de routing del outbox worker
- `auth-backend`: El módulo de auth debe exponer una función de validación JWT reutilizable para WebSocket handshake (no solo HTTP middleware)

## Impact

- **Backend**: Nuevos archivos en `app/features/tutor/` (router, service, models, llm_adapter, schemas)
- **Frontend**: Nuevos archivos en `src/features/student/` (TutorChat component, useTutorStore, useWebSocket hook)
- **DB**: 2 migraciones Alembic (tutor_interactions en operational, tutor_system_prompts en governance)
- **Redis**: Nuevas keys para rate limiting (`tutor:rate:{student_id}:{exercise_id}`)
- **Event Bus**: Nuevos eventos en stream `events:tutor` — consumidos por EPIC-13 (CTR)
- **Dependencies**: `anthropic` SDK (Python), posiblemente `tiktoken` para token counting
