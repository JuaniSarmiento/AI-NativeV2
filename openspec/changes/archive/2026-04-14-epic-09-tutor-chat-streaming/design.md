## Context

Fase 1 entregó ejercicios, submissions, code snapshots, y sandbox de ejecución. El alumno puede escribir código y ejecutarlo, pero no hay interacción pedagógica. EPIC-09 introduce el tutor IA socrático — un chat streaming en tiempo real que guía sin dar respuestas.

Estado actual: existe auth JWT (EPIC-03), Event Bus con outbox (EPIC-01), modelos de ejercicios y submissions (EPICs 06-08), design system con componentes Button/Input/Card/Modal (EPIC-04), y App Shell con routing por rol (EPIC-04).

El tutor usa un system prompt hardcodeado básico. EPIC-10 reemplaza esto con ContextBuilder + guardrails.

## Goals / Non-Goals

**Goals:**
- Chat WebSocket alumno-tutor con streaming token-por-token
- Registro de cada interacción con prompt_hash SHA-256 para reconstrucción
- Rate limiting por alumno por ejercicio (30 msg/hora)
- Producción de eventos para Fase 3 (CTR)
- Frontend integrado en la vista de ejercicio con el design system existente

**Non-Goals:**
- ContextBuilder completo (EPIC-10)
- Guardrails anti-solver (EPIC-10)
- Clasificación N4 automática (EPIC-11 — EPIC-09 solo permite `n4_level` nullable para clasificación posterior)
- Historial de conversaciones entre sesiones (scope futuro)
- Multi-modelo simultáneo (se configura uno, no A/B testing)

## Decisions

### 1. WebSocket sobre HTTP streaming

**Decisión**: WebSocket con FastAPI `WebSocket` endpoint, no SSE ni HTTP streaming.

**Alternativas**:
- SSE (Server-Sent Events): unidireccional, no soporta envío del alumno sin request separado
- HTTP streaming: requiere long-polling o chunked transfer, más complejo para bidireccional

**Razón**: WebSocket es bidireccional nativo. El alumno envía mensajes y recibe tokens en el mismo canal. Además, ya definimos el patrón en la KB (`knowledge-base/02-arquitectura/05_eventos_y_websocket.md`).

### 2. Auth JWT via query param en handshake

**Decisión**: `ws://api/ws/tutor/chat?token=<JWT>` — token en query param, validado en el handshake antes de aceptar la conexión.

**Razón**: WebSocket no soporta headers custom en el handshake del browser. Query param es el patrón estándar. El token se valida UNA vez al conectar, no en cada mensaje.

### 3. Anthropic SDK con streaming directo

**Decisión**: Usar `anthropic` Python SDK con `client.messages.stream()`. Adapter pattern para abstraer el provider.

**Estructura**:
```
app/features/tutor/
├── router.py          # WebSocket endpoint
├── service.py         # TutorService — orquesta chat, persiste, emite eventos
├── llm_adapter.py     # AnthropicAdapter (interface LLMAdapter)
├── schemas.py         # Pydantic schemas para WS messages
├── models.py          # tutor_interactions, tutor_system_prompts
└── rate_limiter.py    # Redis-based rate limiting
```

**Alternativa descartada**: LangChain / LlamaIndex — overhead innecesario, el flujo es request-response con streaming, no hay chains complejos.

### 4. Protocolo de mensajes WebSocket

**Decisión**: JSON messages tipados con discriminated union por `type`:

```
# Cliente → Servidor
{ "type": "chat.message", "content": "...", "exercise_id": "..." }
{ "type": "ping" }

# Servidor → Cliente
{ "type": "chat.token", "content": "..." }           # token individual
{ "type": "chat.done", "interaction_id": "..." }      # fin de respuesta
{ "type": "chat.error", "code": "...", "message": "..." }
{ "type": "rate_limit", "remaining": N, "reset_at": "..." }
{ "type": "pong" }
```

### 5. Rate limiting con Redis sliding window

**Decisión**: Key `tutor:rate:{student_id}:{exercise_id}` con sorted set (timestamp como score). TTL 1 hora. Límite: 30 mensajes/hora por ejercicio.

**Razón**: Sliding window es más justo que fixed window. Redis sorted set con ZRANGEBYSCORE + ZCARD es atómico con Lua script.

### 6. Frontend: ref pattern + design system existente

**Decisión**: WebSocket connection via `useRef` con dos `useEffect`s separados (uno para connection lifecycle, otro para message handling). UI usa componentes del design system (Card, Button, Input). Store Zustand `useTutorStore` con selectores individuales.

**Layout**: El TutorChat se integra como panel derecho en la vista de ejercicio, al lado del Monaco editor. En mobile, es un panel deslizable desde abajo (bottom sheet).

## Risks / Trade-offs

**[Token cost sin control]** → El system prompt básico de EPIC-09 no tiene guardrails contra respuestas largas. Mitigation: `max_tokens` configurable en el adapter (default 1024). EPIC-10 agrega control real.

**[Reconexión pierde contexto]** → Si el WS se desconecta y reconecta, el frontend pierde los mensajes en tránsito. Mitigation: al reconectar, el frontend pide el historial de la sesión actual via REST fallback `GET /api/v1/tutor/sessions/{exercise_id}/messages`.

**[Rate limit UX]** → 30 msg/hora puede frustrar al alumno si no sabe cuántos le quedan. Mitigation: enviar `rate_limit.remaining` después de cada mensaje.

**[Concurrent sessions]** → Un alumno abre el mismo ejercicio en dos pestañas. Mitigation: ambas conexiones WS son independientes, escriben a la misma sesión lógica. Los mensajes se persisten con timestamp, el orden se preserva.

## Open Questions

- ¿El historial REST (`GET /api/v1/tutor/sessions/{exercise_id}/messages`) debería paginarse o devolver toda la sesión? Sesiones largas podrían ser pesadas. **Propuesta**: devolver los últimos 50 mensajes, con paginación hacia atrás.
