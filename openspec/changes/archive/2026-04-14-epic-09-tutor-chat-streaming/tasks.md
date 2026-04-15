## 1. Modelos y Migraciones

- [x] 1.1 Crear modelo SQLAlchemy `tutor_interactions` en `app/features/tutor/models.py` (schema: operational) con todos los campos del spec
- [x] 1.2 Crear modelo SQLAlchemy `tutor_system_prompts` en `app/features/tutor/models.py` (schema: governance) con SHA-256 auto-computed
- [x] 1.3 Generar migración Alembic para ambas tablas con índices (student_id, exercise_id, session_id, sha256_hash unique)
- [x] 1.4 Crear seed data: system prompt socrático básico v1 con `is_active=TRUE`

## 2. Auth WebSocket

- [x] 2.1 Crear `validate_ws_token()` en `app/core/security.py` — validación JWT reutilizable para WS handshake, incluyendo check de blacklist Redis

## 3. LLM Adapter

- [x] 3.1 Definir interface `LLMAdapter` (abstract) con `stream_response()` en `app/features/tutor/llm_adapter.py`
- [x] 3.2 Implementar `AnthropicAdapter` usando `anthropic` SDK con `messages.stream()`, token counting, timeout 30s, max_tokens configurable
- [x] 3.3 Agregar dependencia `anthropic` a `pyproject.toml`
- [x] 3.4 Agregar config LLM a `app/config.py` (model name, max_tokens, timeout)

## 4. Rate Limiter

- [x] 4.1 Implementar `TutorRateLimiter` en `app/features/tutor/rate_limiter.py` — Redis sliding window con sorted set, 30 msg/hora por alumno por ejercicio, key `tutor:rate:{student_id}:{exercise_id}`

## 5. Tutor Service

- [x] 5.1 Crear `TutorService` en `app/features/tutor/service.py` — orquesta: validar exercise, check rate limit, cargar prompt activo, llamar LLM, persistir ambos turnos (user + assistant), emitir eventos
- [x] 5.2 Crear Pydantic schemas en `app/features/tutor/schemas.py` — WSMessage discriminated union (chat.message, ping), WSResponse (chat.token, chat.done, chat.error, rate_limit, pong, connected)
- [x] 5.3 Crear repository `TutorRepository` para queries de tutor_interactions y tutor_system_prompts

## 6. WebSocket Endpoint

- [x] 6.1 Crear WebSocket router en `app/features/tutor/router.py` — endpoint `/ws/tutor/chat`, auth via query param, message loop, heartbeat, timeout 60s
- [x] 6.2 Registrar router en `app/main.py`
- [x] 6.3 Implementar session tracking — detectar primer mensaje para emitir `tutor.session.started`, emitir `tutor.session.ended` en disconnect

## 7. REST Fallback

- [x] 7.1 Endpoint `GET /api/v1/tutor/sessions/{exercise_id}/messages` — últimos 50 mensajes de la sesión más reciente, paginación hacia atrás

## 8. Event Bus Integration

- [x] 8.1 Emitir eventos `tutor.session.started`, `tutor.interaction.completed`, `tutor.session.ended` al outbox con payloads definidos en spec
- [x] 8.2 Agregar routing de eventos `tutor.*` → `events:tutor` en el outbox worker (si no existe mapping formal, agregarlo)

## 9. Frontend — Store y Hook

- [x] 9.1 Crear `useTutorStore` en `src/features/tutor/store.ts` — messages, isConnected, isStreaming, remainingMessages, actions (addMessage, setStreaming, setConnected, clearMessages)
- [x] 9.2 Crear `useWebSocketTutor` hook en `src/features/tutor/hooks/useWebSocketTutor.ts` — ref pattern, dos useEffects, exponential backoff reconnect, cleanup

## 10. Frontend — TutorChat Component

- [x] 10.1 Crear `TutorChat` component — message list con Card, input con Button, typing indicator, rate limit display. Usar design system existente (Card, Button, Input)
- [x] 10.2 Crear `ChatMessage` sub-component — burbuja alumno (derecha) vs tutor (izquierda), streaming cursor, timestamp
- [x] 10.3 Integrar en vista de ejercicio — panel derecho desktop (resizable), bottom sheet mobile
- [x] 10.4 Manejar estados: connecting, connected, disconnected, reconnecting con feedback visual

## 11. Tests

- [x] 11.1 Tests unitarios: TutorService (mock LLM adapter, mock repo)
- [x] 11.2 Tests unitarios: AnthropicAdapter (mock SDK responses)
- [x] 11.3 Tests unitarios: TutorRateLimiter (mock Redis)
- [x] 11.4 Tests integración: WebSocket endpoint (connect, send message, receive stream, heartbeat, auth rejection, rate limit)
- [x] 11.5 Tests integración: REST fallback endpoint
