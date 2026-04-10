---
name: websocket-patterns
description: >
  Ciclo de vida WebSocket para streaming del tutor IA. Auth JWT en el handshake via
  query param ?token=. Streaming de tokens LLM. Reconexión con exponential backoff.
  Heartbeat ping/pong. Patrón de ref en frontend con dos useEffects separados.
  Trigger: cuando se trabaje en conexiones WebSocket, streaming del tutor, o features en tiempo real.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al implementar o modificar el endpoint WebSocket del tutor socrático
- Al agregar streaming de tokens LLM a través de la conexión
- Al implementar el cliente WebSocket en React 19 con Zustand 5
- Al configurar reconexión automática o heartbeat ping/pong
- Al revisar cualquier archivo que importe `WebSocket` de FastAPI o use `useRef` para sockets

## Patrones Críticos

### 1. Endpoint FastAPI con Auth JWT en el Handshake

El token se valida **antes** de aceptar la conexión. Si falla, se cierra con código 1008.

```python
# api/v1/ws/tutor.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.security import decode_access_token
from app.infrastructure.redis.rate_limiter import check_rate_limit
from app.infrastructure.redis.keys import key_ratelimit
from app.dependencies import get_redis

router = APIRouter()

@router.websocket("/ws/tutor/{session_id}")
async def tutor_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),  # ?token=<jwt>
):
    # 1. Validar JWT ANTES de aceptar
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id: str = payload["sub"]
    redis = await get_redis()

    # 2. Rate limit: 30 msg/hora para el tutor
    allowed, remaining = await check_rate_limit(
        redis, user_id, "tutor_ws", limit=30, window_seconds=3600
    )
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            await stream_tutor_response(websocket, user_id, session_id, data)
    except WebSocketDisconnect:
        pass
    finally:
        await redis.aclose()
```

### 2. Streaming LLM Token a Token por WebSocket

Cada token del modelo se envía inmediatamente. Al final, se envía `{"type": "done"}`.

```python
# services/tutor_streamer.py

from fastapi import WebSocket
from app.core.llm import get_llm_client  # cliente async del modelo N4

async def stream_tutor_response(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    message: dict,
) -> None:
    """Hace streaming del tutor socrático token a token."""
    llm = get_llm_client()
    prompt = message.get("content", "")

    try:
        async for chunk in llm.stream(
            prompt=prompt,
            system="Sos un tutor socrático. Nunca des la respuesta directa.",
        ):
            token = chunk.get("text", "")
            if token:
                await websocket.send_json({"type": "token", "data": token})

        # Señal de fin de stream
        await websocket.send_json({"type": "done", "session_id": session_id})

    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
```

### 3. Patrón de Ref en Frontend con Dos useEffects

Un `useEffect` maneja el ciclo de vida de la conexión. El otro suscribe al store de Zustand.
**Nunca mezclarlos**: si se combinan, cada cambio del store reconecta el socket.

```typescript
// hooks/useTutorSocket.ts

import { useEffect, useRef } from "react";
import { useTutorStore } from "@/store/tutorStore";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useTutorSocket(sessionId: string, token: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const appendToken = useTutorStore((s) => s.appendToken);
  const setStatus = useTutorStore((s) => s.setConnectionStatus);

  // Effect 1: ciclo de vida de la conexion WS (solo sessionId y token como deps)
  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/tutor/${sessionId}?token=${token}`);
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as TutorMessage;
      if (msg.type === "token") {
        appendToken(msg.data);
      } else if (msg.type === "done") {
        useTutorStore.getState().finalizeMessage();
      }
    };

    return () => {
      ws.close(1000, "component unmount");
      wsRef.current = null;
    };
  }, [sessionId, token]); // <-- NO incluir appendToken ni setStatus aqui

  // Effect 2: suscripcion a acciones del store que disparan mensajes WS
  useEffect(() => {
    const unsubscribe = useTutorStore.subscribe(
      (state) => state.pendingMessage,
      (pendingMessage) => {
        if (pendingMessage && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ content: pendingMessage }));
          useTutorStore.getState().clearPendingMessage();
        }
      }
    );
    return unsubscribe;
  }, []); // <-- sin deps: se monta una vez, lee wsRef por ref

  return wsRef;
}
```

### 4. Reconexion con Exponential Backoff

Se reintenta hasta `MAX_RETRIES` con delay creciente. Se para definitivamente al alcanzar el máximo.

```typescript
// hooks/useWsReconnect.ts

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

export function useWsReconnect(
  connect: () => WebSocket,
  onFatalError: () => void,
) {
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function scheduleReconnect() {
    if (retryRef.current >= MAX_RETRIES) {
      onFatalError();
      return;
    }
    const delay = BASE_DELAY_MS * 2 ** retryRef.current;   // 1s, 2s, 4s, 8s, 16s
    retryRef.current += 1;
    timerRef.current = setTimeout(() => {
      const ws = connect();
      ws.onopen = () => { retryRef.current = 0; };          // reset en exito
      ws.onclose = () => scheduleReconnect();
    }, delay);
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return { scheduleReconnect };
}
```

## Anti-patrones

### DON'T: Aceptar la conexion antes de validar el token

```python
# MAL — cualquier cliente anónimo puede conectarse y consumir recursos
await websocket.accept()
payload = decode_access_token(token)
if payload is None:
    await websocket.send_json({"error": "unauthorized"})
```

```python
# BIEN — validar primero, aceptar después
payload = decode_access_token(token)
if payload is None:
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
await websocket.accept()
```

### DON'T: Olvidar el cleanup en useEffect (zombie connections)

```typescript
// MAL — la conexion queda viva después de desmontar el componente
useEffect(() => {
  const ws = new WebSocket(url);
  wsRef.current = ws;
  // sin return cleanup
}, []);
```

```typescript
// BIEN — siempre cleanup explícito
useEffect(() => {
  const ws = new WebSocket(url);
  wsRef.current = ws;
  return () => ws.close(1000, "component unmount");
}, []);
```

### DON'T: Reintentar infinitamente sin backoff ni limite

```typescript
// MAL — DoS al propio servidor si se cae
ws.onclose = () => setTimeout(() => connect(), 100);
```

```typescript
// BIEN — exponential backoff con MAX_RETRIES=5
ws.onclose = () => scheduleReconnect();  // usa useWsReconnect
```

### DON'T: Mutar estado React directo desde el mensaje WS

```typescript
// MAL — setState fuera de contexto React puede causar batching incorrecta
ws.onmessage = (e) => setTokens((prev) => [...prev, e.data]);
```

```typescript
// BIEN — llamar accion del store de Zustand
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  useTutorStore.getState().appendToken(msg.data);
};
```

## Checklist

- [ ] El JWT se valida ANTES de `websocket.accept()`, con cierre `1008` si falla
- [ ] El rate limit (30 msg/hora) se chequea en el handshake, no en cada mensaje
- [ ] El streaming usa `send_json({"type": "token", "data": token})` por chunk
- [ ] Al finalizar el stream se envía `{"type": "done", "session_id": session_id}`
- [ ] Los errores del LLM se capturan y se envían como `{"type": "error", "message": ...}`
- [ ] El frontend usa dos `useEffect` separados (lifecycle vs store subscription)
- [ ] El cleanup del `useEffect` cierra el socket con código `1000`
- [ ] El exponential backoff tiene `MAX_RETRIES=5` y `BASE_DELAY_MS=1000`
- [ ] Ningún `setState` de React se llama directamente desde `onmessage`
- [ ] El `wsRef` se usa para enviar mensajes, no se re-crea en cada render
