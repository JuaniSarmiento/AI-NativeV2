# 05 — Eventos y WebSocket: Arquitectura de Tiempo Real

**Plataforma AI-Native — UTN FRM — Documentación de Arquitectura**
**Versión:** 1.0 | **Estado:** Vigente | **Fase:** Transversal (Fases 1, 2 y 3)

---

## Tabla de Contenidos

1. [Introducción y Contexto](#1-introducción-y-contexto)
2. [Arquitectura WebSocket para Streaming del Tutor](#2-arquitectura-websocket-para-streaming-del-tutor)
3. [Protocolo de Mensajes](#3-protocolo-de-mensajes)
4. [Autenticación y Seguridad en WebSocket](#4-autenticación-y-seguridad-en-websocket)
5. [Reconexión con Backoff Exponencial](#5-reconexión-con-backoff-exponencial)
6. [Heartbeat y Ping-Pong](#6-heartbeat-y-ping-pong)
7. [Arquitectura del Event Bus entre Fases](#7-arquitectura-del-event-bus-entre-fases)
8. [Esquema Canónico de Eventos](#8-esquema-canónico-de-eventos)
9. [Eventos Producidos por Fase 1](#9-eventos-producidos-por-fase-1)
10. [Eventos Producidos por Fase 2](#10-eventos-producidos-por-fase-2)
11. [Consumer de Fase 3](#11-consumer-de-fase-3)
12. [Code Snapshots como Eventos](#12-code-snapshots-como-eventos)
13. [Enumeración de Tipos de Eventos Cognitivos y Mapeo N4](#13-enumeración-de-tipos-de-eventos-cognitivos-y-mapeo-n4)
14. [Diagramas de Flujo](#14-diagramas-de-flujo)
15. [Consideraciones de Escalabilidad](#15-consideraciones-de-escalabilidad)

---

## 1. Introducción y Contexto

La plataforma AI-Native opera en tiempo real en dos dimensiones ortogonales:

1. **Streaming de respuestas del tutor IA**: El modelo de lenguaje (Claude via Anthropic API) genera texto token a token. Para una experiencia conversacional fluida, esos tokens deben llegar al navegador del estudiante de forma incremental, sin esperar la respuesta completa.

2. **Bus de eventos entre fases**: Las acciones del estudiante en Fase 1 (ejercicios, ejecución de código) y Fase 2 (interacción con el tutor) generan eventos semánticos que Fase 3 debe consumir para clasificar el estado cognitivo del estudiante según el modelo N4 (Neuro-Learning Levels).

Estas dos dimensiones se implementan con tecnologías distintas pero complementarias:

- **WebSocket** (protocolo RFC 6455) para la comunicación bidireccional cliente-servidor en tiempo real.
- **Redis Pub/Sub** (opción primaria) o **tabla outbox en PostgreSQL** (opción de fallback) para el bus de eventos entre procesos del backend.

El diseño prioriza:
- Integridad de los datos cognitivos (no se pueden perder eventos para el CTR).
- Latencia perceptiva baja en el chat del tutor (< 100ms para el primer token).
- Desacoplamiento entre fases (Fase 3 no depende del uptime de Fase 1 o Fase 2).

---

## 2. Arquitectura WebSocket para Streaming del Tutor

### 2.1 Endpoint Principal

```
ws://[host]/ws/tutor/chat
wss://[host]/ws/tutor/chat  (producción con TLS)
```

El endpoint es gestionado por el módulo `phase2` de la aplicación FastAPI. Cada conexión WebSocket representa una sesión de chat activa entre un estudiante y el tutor IA.

### 2.2 Ciclo de Vida de una Conexión

```
[Cliente]                        [Servidor FastAPI]                [Anthropic API]
    |                                    |                               |
    |-- ws://host/ws/tutor/chat?token=JWT -->                           |
    |                                    |-- Validar JWT               |
    |                                    |-- Resolver student_id       |
    |                                    |-- Cargar session_id activo  |
    |<-- HTTP 101 Switching Protocols ---|                               |
    |                                    |                               |
    |-- { message, current_code } ------>|                               |
    |                                    |-- stream_message() --------->|
    |<-- { chunk: "Hola", done: false } -|<-- token "Hola" ------------|
    |<-- { chunk: ",", done: false } ----|<-- token "," ---------------|
    |<-- { chunk: " ¿cómo", done:false } |<-- token " ¿cómo" ---------|
    |        ... más chunks ...          |        ... stream ...        |
    |<-- { chunk: "", done: true,        |<-- stream finalizado --------|
    |      classification_n4: "N3" } ----|                               |
    |                                    |-- Publicar evento en bus    |
    |                                    |-- Guardar en DB             |
```

### 2.3 Implementación en FastAPI

```python
# app/phase2/routers/ws_tutor.py

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from app.phase2.services.tutor_service import TutorService
from app.auth.dependencies import get_student_from_ws_token
from app.shared.event_bus import EventBus
import asyncio

router = APIRouter()

@router.websocket("/ws/tutor/chat")
async def ws_tutor_chat(
    websocket: WebSocket,
    token: str = Query(...),
    tutor_service: TutorService = Depends(),
    event_bus: EventBus = Depends(),
):
    # 1. Validar JWT antes de aceptar la conexión
    try:
        student = await get_student_from_ws_token(token)
    except AuthError:
        await websocket.close(code=4001, reason="Token inválido o expirado")
        return

    await websocket.accept()

    # 2. Tarea de heartbeat en background
    heartbeat_task = asyncio.create_task(
        _send_heartbeat(websocket, interval_seconds=30)
    )

    try:
        while True:
            # 3. Recibir mensaje del cliente
            raw = await websocket.receive_json()
            user_message = raw.get("message", "")
            current_code = raw.get("current_code", "")

            if not user_message.strip():
                continue

            # 4. Publicar evento de inicio de interacción
            await event_bus.publish("tutor.interaction.started", {
                "student_id": str(student.id),
                "message_preview": user_message[:100],
            })

            # 5. Streaming token a token desde LLM
            classification = None
            async for chunk, is_done, meta in tutor_service.stream_response(
                student_id=student.id,
                message=user_message,
                current_code=current_code,
            ):
                if is_done:
                    classification = meta.get("classification_n4")
                    await websocket.send_json({
                        "chunk": "",
                        "done": True,
                        "classification_n4": classification,
                    })
                    break
                else:
                    await websocket.send_json({
                        "chunk": chunk,
                        "done": False,
                        "classification_n4": None,
                    })

            # 6. Publicar evento de interacción completada
            await event_bus.publish("tutor.interaction.completed", {
                "student_id": str(student.id),
                "classification_n4": classification,
                "code_snapshot": current_code,
            })

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await tutor_service.close_session(student.id)


async def _send_heartbeat(websocket: WebSocket, interval_seconds: int):
    """Envía ping periódico para mantener la conexión activa."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            break
```

---

## 3. Protocolo de Mensajes

### 3.1 Mensaje del Cliente al Servidor (Upstream)

```typescript
interface TutorChatRequest {
  message: string;         // Pregunta o mensaje del estudiante (requerido)
  current_code: string;    // Snapshot del código actual en el editor (puede ser "")
}
```

**Reglas de validación en el servidor:**
- `message` no puede ser vacío ni solo espacios.
- `current_code` puede ser string vacío; en ese caso el tutor no tendrá contexto de código.
- Si el JSON es malformado, el servidor cierra con código `4003`.

### 3.2 Mensaje del Servidor al Cliente (Downstream — Stream)

```typescript
// Chunk parcial (durante el stream)
interface TutorChunkMessage {
  chunk: string;                     // Fragmento de texto generado
  done: false;
  classification_n4: null;
}

// Mensaje de finalización
interface TutorDoneMessage {
  chunk: "";
  done: true;
  classification_n4: N4Level | null; // Clasificación al completar
}

// Heartbeat
interface PingMessage {
  type: "ping";
}

type N4Level = "N1" | "N2" | "N3" | "N4";
```

### 3.3 Códigos de Cierre WebSocket

| Código | Razón                             | Acción del cliente     |
|--------|-----------------------------------|------------------------|
| 1000   | Cierre normal (usuario cerró tab) | No reconectar          |
| 1001   | Server going away (deploy)        | Reconectar con backoff |
| 1011   | Error interno del servidor        | Reconectar con backoff |
| 4001   | Token JWT inválido o expirado     | Renovar token, luego reconectar |
| 4003   | Payload malformado                | Corregir y reconectar  |
| 4429   | Rate limit excedido               | Esperar y reconectar   |

---

## 4. Autenticación y Seguridad en WebSocket

### 4.1 JWT via Query Parameter

El protocolo WebSocket no permite headers HTTP personalizados en el handshake inicial (el navegador usa la API nativa `new WebSocket(url)` sin control de headers). Por esta razón, el JWT se pasa como query parameter:

```
wss://api.ai-native.edu/ws/tutor/chat?token=eyJhbGciOiJIUzI1NiJ9...
```

**Consideraciones de seguridad:**
- El token en query param puede quedar en logs del servidor web (Nginx, uvicorn). **Se debe excluir `/ws/` de los access logs** o usar log masking.
- El token tiene TTL corto (15 minutos). La reconexión renueva el token automáticamente vía el refresh flow de HTTP.
- En producción, TLS (wss://) protege el token en tránsito.

### 4.2 Validación del Token en el Servidor

```python
# app/auth/dependencies.py

from jose import jwt, JWTError
from app.config import settings

async def get_student_from_ws_token(token: str) -> Student:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        student_id = payload.get("sub")
        role = payload.get("role")

        if role != "student":
            raise AuthError("Solo estudiantes pueden conectarse al tutor")

        student = await StudentRepository.get_by_id(student_id)
        if not student or not student.is_active:
            raise AuthError("Estudiante no encontrado o inactivo")

        return student

    except JWTError:
        raise AuthError("Token JWT inválido")
```

---

## 5. Reconexión con Backoff Exponencial

El frontend implementa reconexión automática con backoff exponencial y jitter para evitar thundering herd (todos los clientes reconectando simultáneamente tras un deploy).

```typescript
// src/features/tutor/hooks/useTutorWebSocket.ts

import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useTutorStore } from "@/stores/tutorStore";

const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;
const MAX_RETRIES = 10;

export function useTutorWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const { accessToken, refreshTokens } = useAuthStore();
  const { appendChunk, setDone, setConnected } = useTutorStore();

  const computeBackoff = (attempt: number): number => {
    const exponential = BASE_DELAY_MS * Math.pow(2, attempt);
    const capped = Math.min(exponential, MAX_DELAY_MS);
    // Jitter: ±20% del delay calculado
    const jitter = capped * 0.2 * (Math.random() * 2 - 1);
    return Math.floor(capped + jitter);
  };

  const connect = useCallback(async () => {
    if (!isMountedRef.current) return;

    // Renovar token si es necesario antes de conectar
    let token = accessToken;
    if (!token) {
      token = await refreshTokens();
      if (!token) return; // No autenticado, no reconectar
    }

    const wsUrl = `${import.meta.env.VITE_WS_URL}/ws/tutor/chat?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      retryCountRef.current = 0; // Reset contador al conectar exitosamente
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
        return;
      }

      if (data.done) {
        setDone(data.classification_n4);
      } else if (data.chunk) {
        appendChunk(data.chunk);
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      wsRef.current = null;

      // No reconectar en cierre normal o token inválido
      if (event.code === 1000 || event.code === 4001) return;

      if (retryCountRef.current >= MAX_RETRIES) {
        console.error("WebSocket: máximo de reintentos alcanzado");
        return;
      }

      const delay = computeBackoff(retryCountRef.current);
      retryCountRef.current += 1;

      retryTimeoutRef.current = setTimeout(() => {
        if (isMountedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // El error siempre va seguido de onclose, se maneja ahí
    };
  }, [accessToken, refreshTokens, appendChunk, setDone, setConnected]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      wsRef.current?.close(1000);
    };
  }, [connect]);

  const sendMessage = useCallback((message: string, currentCode: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message, current_code: currentCode }));
    }
  }, []);

  return { sendMessage };
}
```

---

## 6. Heartbeat y Ping-Pong

Las conexiones WebSocket inactivas pueden ser cerradas por proxies, load balancers o NAT gateways con timeouts de idle (típicamente 60-90 segundos en AWS ALB, Nginx, Cloudflare).

### 6.1 Estrategia

- **Servidor → Cliente**: el servidor envía `{ "type": "ping" }` cada 30 segundos.
- **Cliente → Servidor**: al recibir un ping, el cliente responde con `{ "type": "pong" }`.
- Si el servidor no recibe pong en 10 segundos, asume conexión zombie y la cierra con código 1011.

### 6.2 Implementación en el Servidor

```python
# app/phase2/services/websocket_manager.py

import asyncio
from fastapi import WebSocket

class ConnectionManager:
    PING_INTERVAL = 30  # segundos
    PONG_TIMEOUT = 10   # segundos

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._pong_received: dict[str, asyncio.Event] = {}

    async def connect(self, student_id: str, websocket: WebSocket):
        self._connections[student_id] = websocket
        self._pong_received[student_id] = asyncio.Event()

    async def disconnect(self, student_id: str):
        self._connections.pop(student_id, None)
        self._pong_received.pop(student_id, None)

    async def heartbeat_loop(self, student_id: str, websocket: WebSocket):
        while student_id in self._connections:
            await asyncio.sleep(self.PING_INTERVAL)

            # Enviar ping
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

            # Esperar pong
            self._pong_received[student_id].clear()
            try:
                await asyncio.wait_for(
                    self._pong_received[student_id].wait(),
                    timeout=self.PONG_TIMEOUT,
                )
            except asyncio.TimeoutError:
                # Conexión zombie — cerrar
                await websocket.close(code=1011, reason="Pong timeout")
                break

    def mark_pong(self, student_id: str):
        if event := self._pong_received.get(student_id):
            event.set()


manager = ConnectionManager()
```

---

## 7. Arquitectura del Event Bus entre Fases

### 7.1 Motivación

Las Fases 1, 2 y 3 son módulos independientes dentro del mismo monolito. Sin embargo, la Fase 3 (clasificación cognitiva) necesita conocer eventos de Fase 1 (ejecuciones, submissions) y Fase 2 (interacciones con el tutor) para construir el CTR y clasificar el estado cognitivo del estudiante.

**Opciones evaluadas:**

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| Llamada directa función | Simple | Acoplamiento fuerte, si Fase 3 falla bloquea Fase 1/2 |
| HTTP entre módulos | Independencia de deploy | Latencia, manejo de errores distribuido |
| Redis Pub/Sub | Desacoplado, bajo latencia | At-most-once delivery (puede perder mensajes) |
| DB Outbox Table | At-least-once, auditable, transaccional | Polling delay, más complejo |

**Decisión**: implementación dual — **Redis Pub/Sub como canal principal** (baja latencia) con **tabla outbox en PostgreSQL como fallback** para garantizar at-least-once delivery de eventos críticos del CTR.

### 7.2 Topología de Canales Redis

```
Canal Redis                    Productor         Consumidor
─────────────────────────────────────────────────────────
ai-native:events:code          Fase 1 (code exec) Fase 3 worker
ai-native:events:submission    Fase 1 (submit)    Fase 3 worker
ai-native:events:tutor         Fase 2 (chat)      Fase 3 worker
ai-native:events:governance    Fase 4 (admin)     Fase 3 worker (opcional)
```

### 7.3 Implementación del Event Bus

```python
# app/shared/event_bus.py

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.shared.models import EventOutbox


class EventBus:
    """
    Event Bus con publicación dual: Redis Pub/Sub + outbox en DB.

    Redis: delivery inmediato, at-most-once.
    Outbox: garantía de at-least-once para eventos críticos (CTR).
    """

    def __init__(self, redis: aioredis.Redis, db: AsyncSession):
        self._redis = redis
        self._db = db

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        source: str = "system",
        critical: bool = False,
    ) -> str:
        """
        Publica un evento.

        Args:
            event_type: Tipo del evento (ej: "code.executed", "tutor.interaction.completed")
            payload: Datos del evento.
            source: Módulo origen ("phase1", "phase2", "phase3").
            critical: Si True, también persiste en outbox para garantía at-least-once.

        Returns:
            ID del evento generado.
        """
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "source": source,
            "event_type": event_type,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Publicar en Redis (at-most-once, baja latencia)
        channel = f"ai-native:events:{event_type.split('.')[0]}"
        await self._redis.publish(channel, json.dumps(event))

        # 2. Si es crítico, persistir en outbox (at-least-once)
        if critical:
            outbox_entry = EventOutbox(
                id=event_id,
                source=source,
                event_type=event_type,
                payload=payload,
                processed=False,
                created_at=datetime.now(timezone.utc),
            )
            self._db.add(outbox_entry)
            await self._db.flush()

        return event_id
```

---

## 8. Esquema Canónico de Eventos

### 8.1 Modelo de la Tabla Outbox

```python
# app/shared/models/event_outbox.py

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database import Base
from datetime import datetime


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    __table_args__ = {"schema": "operational"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Módulo origen: phase1, phase2, phase3, phase4",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Tipo de evento: code.executed, tutor.interaction.completed, etc.",
    )
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Datos del evento. Schema varía según event_type.",
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="True cuando Phase 3 procesó el evento.",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    retry_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Cantidad de reintentos de procesamiento.",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Último error de procesamiento, si aplica.",
    )
```

### 8.2 Schema JSON de Eventos (TypeScript)

```typescript
// src/types/events.ts

export interface BaseEvent {
  id: string;                   // UUID v4
  source: EventSource;          // Módulo origen
  event_type: EventType;        // Tipo de evento
  payload: Record<string, unknown>;
  processed: boolean;
  created_at: string;           // ISO 8601
}

export type EventSource = "phase1" | "phase2" | "phase3" | "phase4";

export type EventType =
  // Fase 1 — Ejercicios y Ejecución
  | "code.snapshot.captured"
  | "code.executed"
  | "code.execution.failed"
  | "exercise.submitted"
  | "exercise.graded"
  | "test.passed"
  | "test.failed"
  // Fase 2 — Tutor IA
  | "tutor.session.started"
  | "tutor.interaction.started"
  | "tutor.interaction.completed"
  | "tutor.session.ended"
  | "tutor.hint.requested"
  | "tutor.hint.provided"
  // Fase 3 — Clasificación Cognitiva
  | "cognitive.classified"
  | "ctr.entry.created"
  | "ctr.hash.verified"
  // Fase 4 — Gobernanza
  | "governance.flag.raised"
  | "governance.review.completed";
```

---

## 9. Eventos Producidos por Fase 1

### 9.1 code.executed

Disparado cuando el estudiante ejecuta su código en el sandbox.

```json
{
  "id": "a3f1c2d4-...",
  "source": "phase1",
  "event_type": "code.executed",
  "payload": {
    "student_id": "uuid",
    "exercise_id": "uuid",
    "session_id": "uuid",
    "code": "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)",
    "language": "python",
    "stdout": "120\n",
    "stderr": "",
    "exit_code": 0,
    "execution_time_ms": 45,
    "test_results": [
      { "test_id": "t1", "passed": true, "expected": "120", "actual": "120" }
    ],
    "timestamp": "2026-04-10T14:32:00Z"
  },
  "processed": false,
  "created_at": "2026-04-10T14:32:00Z"
}
```

### 9.2 exercise.submitted

Disparado cuando el estudiante envía una solución final.

```json
{
  "source": "phase1",
  "event_type": "exercise.submitted",
  "payload": {
    "student_id": "uuid",
    "exercise_id": "uuid",
    "submission_id": "uuid",
    "final_code": "...",
    "attempt_number": 3,
    "all_tests_passed": true,
    "score": 100,
    "time_spent_seconds": 840
  }
}
```

---

## 10. Eventos Producidos por Fase 2

### 10.1 tutor.interaction.completed

El más importante para Fase 3: contiene el snapshot de código y la clasificación preliminar N4.

```json
{
  "source": "phase2",
  "event_type": "tutor.interaction.completed",
  "payload": {
    "student_id": "uuid",
    "session_id": "uuid",
    "interaction_id": "uuid",
    "user_message": "¿Por qué mi función devuelve None?",
    "assistant_response_length": 312,
    "code_snapshot": "def factorial(n):\n    if n == 0:\n        return 1\n    factorial(n-1)",
    "classification_n4": "N2",
    "classification_confidence": 0.87,
    "model_used": "claude-opus-4-5",
    "tokens_used": { "input": 450, "output": 180 },
    "duration_ms": 2340,
    "timestamp": "2026-04-10T14:35:22Z"
  }
}
```

---

## 11. Consumer de Fase 3

Fase 3 tiene un worker que consume eventos de dos fuentes en paralelo:

```python
# app/phase3/workers/event_consumer.py

import asyncio
import json
from app.shared.event_bus import CHANNELS
from app.phase3.services.cognitive_classifier import CognitiveClassifier


class Phase3EventConsumer:
    """
    Consume eventos de Phase 1 y Phase 2 para clasificación cognitiva.

    Estrategia dual:
    1. Redis Pub/Sub para procesamiento en tiempo real (baja latencia).
    2. Outbox polling cada 5s como fallback para eventos no procesados.
    """

    def __init__(self, redis, db_session_factory, classifier: CognitiveClassifier):
        self._redis = redis
        self._db_factory = db_session_factory
        self._classifier = classifier

    async def start(self):
        await asyncio.gather(
            self._redis_consumer(),
            self._outbox_poller(),
        )

    async def _redis_consumer(self):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(
            "ai-native:events:code",
            "ai-native:events:submission",
            "ai-native:events:tutor",
        )

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            event = json.loads(message["data"])
            await self._process_event(event)

    async def _outbox_poller(self):
        """Procesa eventos críticos no procesados del outbox."""
        while True:
            await asyncio.sleep(5)
            async with self._db_factory() as db:
                unprocessed = await EventOutboxRepository.get_unprocessed(
                    db, limit=50
                )
                for event in unprocessed:
                    try:
                        await self._process_event(event.to_dict())
                        await EventOutboxRepository.mark_processed(db, event.id)
                    except Exception as e:
                        await EventOutboxRepository.increment_retry(
                            db, event.id, str(e)
                        )

    async def _process_event(self, event: dict):
        event_type = event.get("event_type")

        handlers = {
            "code.executed": self._handle_code_executed,
            "code.snapshot.captured": self._handle_snapshot,
            "tutor.interaction.completed": self._handle_tutor_interaction,
            "exercise.submitted": self._handle_submission,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event["payload"])

    async def _handle_tutor_interaction(self, payload: dict):
        await self._classifier.classify_and_record(
            student_id=payload["student_id"],
            session_id=payload["session_id"],
            interaction_id=payload["interaction_id"],
            event_type="tutor_interaction",
            context=payload,
        )
```

---

## 12. Code Snapshots como Eventos

Para reconstruir el camino cognitivo del estudiante, la plataforma captura snapshots del código del editor en dos momentos:

### 12.1 Snapshot Periódico (cada 30 segundos)

```typescript
// src/features/editor/hooks/useCodeSnapshots.ts

import { useEffect, useRef } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { snapshotApi } from "@/api/snapshotApi";

const SNAPSHOT_INTERVAL_MS = 30_000;

export function useCodeSnapshots(exerciseId: string) {
  const { code } = useEditorStore();
  const lastSnapshotRef = useRef<string>("");

  useEffect(() => {
    const interval = setInterval(async () => {
      // Solo enviar si el código cambió desde el último snapshot
      if (code !== lastSnapshotRef.current && code.trim()) {
        await snapshotApi.capture({
          exerciseId,
          code,
          trigger: "periodic",
        });
        lastSnapshotRef.current = code;
      }
    }, SNAPSHOT_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [code, exerciseId]);
}
```

### 12.2 Snapshot en Ejecución

Cada vez que el estudiante ejecuta su código, el snapshot se incluye automáticamente en el evento `code.executed` (ver sección 9.1). No hay un evento separado para este caso.

### 12.3 Endpoint REST para Snapshots

```
POST /api/v1/phase1/exercises/{exercise_id}/snapshots
Content-Type: application/json

{
  "code": "...",
  "trigger": "periodic" | "execution" | "submission"
}
```

El backend procesa este request y publica el evento `code.snapshot.captured` en el bus.

---

## 13. Enumeración de Tipos de Eventos Cognitivos y Mapeo N4

El modelo N4 (Neuro-Learning Levels) clasifica el estado cognitivo del estudiante en cuatro niveles basados en sus interacciones. La Fase 3 mapea cada tipo de evento a indicadores N4.

### 13.1 Niveles N4

| Nivel | Nombre          | Descripción                                              |
|-------|-----------------|----------------------------------------------------------|
| N1    | Desorientación  | El estudiante no comprende el problema ni las herramientas |
| N2    | Reconocimiento  | Identifica conceptos pero no puede aplicarlos            |
| N3    | Aplicación      | Aplica conceptos con guía; comete errores recuperables    |
| N4    | Autonomía       | Resuelve problemas de forma independiente y fluida        |

### 13.2 Mapeo de Eventos a Indicadores N4

```python
# app/phase3/domain/n4_mapping.py

from enum import Enum


class N4Level(str, Enum):
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    N4 = "N4"


class CognitiveEventType(str, Enum):
    # Indicadores de N1 — Desorientación
    REPEATED_SAME_ERROR = "repeated_same_error"
    ASKED_BASIC_CONCEPT = "asked_basic_concept"
    NO_PROGRESS_10MIN = "no_progress_10min"
    BLANK_CODE_START = "blank_code_start"
    REQUESTED_FULL_SOLUTION = "requested_full_solution"

    # Indicadores de N2 — Reconocimiento
    IDENTIFIED_CONCEPT = "identified_concept"
    ASKED_HOW_TO_APPLY = "asked_how_to_apply"
    SYNTAX_ERROR_RESOLVED_WITH_HINT = "syntax_error_resolved_with_hint"
    COPIED_TUTOR_EXAMPLE = "copied_tutor_example"

    # Indicadores de N3 — Aplicación
    FIXED_LOGIC_ERROR_INDEPENDENTLY = "fixed_logic_error_independently"
    ASKED_OPTIMIZATION = "asked_optimization"
    TESTS_PASSING_WITH_SOME_HELP = "tests_passing_with_some_help"
    EXPLAINED_APPROACH_TO_TUTOR = "explained_approach_to_tutor"

    # Indicadores de N4 — Autonomía
    ALL_TESTS_PASS_FIRST_ATTEMPT = "all_tests_pass_first_attempt"
    NO_TUTOR_INTERACTION_NEEDED = "no_tutor_interaction_needed"
    SOLVED_EDGE_CASES = "solved_edge_cases"
    REFACTORED_INDEPENDENTLY = "refactored_independently"
    HELPED_CLASSMATE = "helped_classmate"


# Mapeo de tipo de evento a nivel N4 sugerido
EVENT_TO_N4_HINT: dict[CognitiveEventType, N4Level] = {
    CognitiveEventType.REPEATED_SAME_ERROR: N4Level.N1,
    CognitiveEventType.ASKED_BASIC_CONCEPT: N4Level.N1,
    CognitiveEventType.NO_PROGRESS_10MIN: N4Level.N1,
    CognitiveEventType.BLANK_CODE_START: N4Level.N1,
    CognitiveEventType.REQUESTED_FULL_SOLUTION: N4Level.N1,
    CognitiveEventType.IDENTIFIED_CONCEPT: N4Level.N2,
    CognitiveEventType.ASKED_HOW_TO_APPLY: N4Level.N2,
    CognitiveEventType.SYNTAX_ERROR_RESOLVED_WITH_HINT: N4Level.N2,
    CognitiveEventType.COPIED_TUTOR_EXAMPLE: N4Level.N2,
    CognitiveEventType.FIXED_LOGIC_ERROR_INDEPENDENTLY: N4Level.N3,
    CognitiveEventType.ASKED_OPTIMIZATION: N4Level.N3,
    CognitiveEventType.TESTS_PASSING_WITH_SOME_HELP: N4Level.N3,
    CognitiveEventType.EXPLAINED_APPROACH_TO_TUTOR: N4Level.N3,
    CognitiveEventType.ALL_TESTS_PASS_FIRST_ATTEMPT: N4Level.N4,
    CognitiveEventType.NO_TUTOR_INTERACTION_NEEDED: N4Level.N4,
    CognitiveEventType.SOLVED_EDGE_CASES: N4Level.N4,
    CognitiveEventType.REFACTORED_INDEPENDENTLY: N4Level.N4,
    CognitiveEventType.HELPED_CLASSMATE: N4Level.N4,
}
```

### 13.3 Lógica de Clasificación Final

La clasificación final no es la de un solo evento sino una ponderación temporal de los últimos N eventos dentro de la sesión cognitiva activa:

```python
# app/phase3/services/cognitive_classifier.py

from collections import Counter
from datetime import datetime, timedelta, timezone

CLASSIFICATION_WINDOW_MINUTES = 15
N4_WEIGHTS = {"N1": 1, "N2": 2, "N3": 3, "N4": 4}

def classify_session(events: list[CognitiveCTREntry]) -> N4Level:
    """
    Clasifica el nivel N4 actual del estudiante basándose
    en los eventos de los últimos CLASSIFICATION_WINDOW_MINUTES minutos.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=CLASSIFICATION_WINDOW_MINUTES)
    recent = [e for e in events if e.created_at >= cutoff]

    if not recent:
        return N4Level.N1

    level_counts = Counter(e.n4_level for e in recent)
    weighted = {
        level: count * N4_WEIGHTS[level]
        for level, count in level_counts.items()
    }

    return max(weighted, key=weighted.get)
```

---

## 14. Diagramas de Flujo

### 14.1 Flujo Completo de una Interacción con el Tutor

```
Estudiante escribe código → Cada 30s snapshot → evento code.snapshot.captured → Phase 3

Estudiante hace pregunta al tutor:
  Frontend → WebSocket → /ws/tutor/chat
    → Validar JWT
    → TutorService.stream_response()
      → LLM Adapter → Anthropic API (streaming SSE)
        → token "La" → WS → Frontend (append chunk)
        → token " función" → WS → Frontend (append chunk)
        → ... N tokens ...
        → [DONE] classification_n4 = "N2"
    → EventBus.publish("tutor.interaction.completed", critical=True)
      → Redis Pub/Sub → Phase3 worker (inmediato)
      → DB Outbox (garantía)
    → Phase3 worker procesa → CTR entry → hash chaining → DB

Frontend muestra respuesta completa con clasificación N4 en sidebar
```

### 14.2 Flujo de Reconexión

```
t=0:00  WebSocket conectado
t=0:30  Server envía ping → Client responde pong
t=1:00  Server envía ping → Client responde pong
t=1:15  Servidor se reinicia (deploy)
t=1:15  WebSocket cierra con código 1001
t=1:15  Cliente detecta onclose → intento 1 → delay 1000ms
t=1:16  Reconecta exitosamente (nuevo pod levantado)
t=1:16  retryCount = 0 (reset)
```

---

## 15. Consideraciones de Escalabilidad

### 15.1 Límites Actuales

| Recurso | Límite actual | Motivo |
|---------|---------------|--------|
| Conexiones WS simultáneas | ~500 por proceso | Límite de file descriptors en uvicorn |
| Eventos en outbox sin procesar | Sin límite (DB) | Riesgo de acumulación si Phase 3 cae |
| Snapshots por sesión | Sin límite | Storage en PostgreSQL, riesgo de crecimiento |

### 15.2 Estrategias de Escalado

**Corto plazo (v1 — tesis):**
- Un solo proceso uvicorn con workers async: suficiente para 30-50 estudiantes concurrentes (escenario de aula).
- Redis Pub/Sub en mismo nodo que la app.

**Mediano plazo (producción universitaria):**
- uvicorn detrás de Nginx con múltiples workers.
- Redis Cluster para Pub/Sub.
- Tabla outbox con índice en `(processed, created_at)` para polling eficiente.
- Limit snapshots a 1 por minuto por estudiante (debounce en backend).

### 15.3 Índices Recomendados

```sql
-- Para el outbox poller de Phase 3
CREATE INDEX CONCURRENTLY idx_event_outbox_unprocessed
ON operational.event_outbox (processed, created_at)
WHERE processed = false;

-- Para consultas por estudiante
CREATE INDEX CONCURRENTLY idx_event_outbox_student
ON operational.event_outbox ((payload->>'student_id'), created_at DESC);
```

---

*Documento generado para el proyecto AI-Native — UTN FRM. Tesis doctoral sobre evaluación cognitiva asistida por IA en educación en programación.*
