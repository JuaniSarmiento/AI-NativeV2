---
name: redis-best-practices
description: >
  Convenciones de naming de claves Redis, políticas de TTL, Redis Streams para el event bus
  entre fases, rate limiting con sliding window y blacklist de tokens JWT.
  Trigger: cuando se trabaje con Redis — cache, event bus, rate limiting o gestión de tokens.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o acceder a cualquier clave Redis en el proyecto
- Al implementar rate limiting (tutor: 30 msg/hora por ejercicio, general: 100 req/min)
- Al gestionar blacklist de tokens JWT después de refresh rotation
- Al publicar o consumir eventos entre las fases del pipeline (Phase 1/2 → Phase 3)
- Al revisar código que usa `redis.asyncio` o `aioredis`

## Patrones Críticos

### 1. Convención de Naming con Builder Functions

**Nunca** concatenar strings a mano. Siempre usar las builder functions centralizadas.

```python
# infrastructure/redis/keys.py

from enum import StrEnum

class RedisDomain(StrEnum):
    CACHE    = "cache"
    RL       = "rl"
    BLACKLIST = "blacklist"
    EVENTS   = "events"
    SESSION  = "session"

def key_cache(entity: str, entity_id: str) -> str:
    """ainative:cache:{entity}:{id}"""
    return f"ainative:{RedisDomain.CACHE}:{entity}:{entity_id}"

def key_tutor_ratelimit(user_id: str, exercise_id: str) -> str:
    """rl:tutor:{user_id}:{exercise_id}"""
    return f"rl:tutor:{user_id}:{exercise_id}"

def key_login_ratelimit(ip: str) -> str:
    """rl:login:{ip}"""
    return f"rl:login:{ip}"

def key_token_blacklist(jti: str) -> str:
    """ainative:blacklist:token:{jti}"""
    return f"ainative:{RedisDomain.BLACKLIST}:token:{jti}"

def key_session(user_id: str) -> str:
    """ainative:session:{user_id}"""
    return f"ainative:{RedisDomain.SESSION}:{user_id}"
```

### 2. Sliding Window Rate Limiter con Pipeline

Rate limits del proyecto: **30 msg/hora por alumno por ejercicio** para el tutor IA, **100 req/min** general.

```python
# infrastructure/redis/rate_limiter.py

import time
from redis.asyncio import Redis
from app.infrastructure.redis.keys import key_tutor_ratelimit, key_login_ratelimit

async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding window rate limiter. Retorna (allowed, remaining).
    Ejemplo: limit=30, window_seconds=3600 → tutor endpoint.
    """
    now = time.time()
    window_start = now - window_seconds

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, "-inf", window_start)   # limpiar entradas viejas
        pipe.zadd(key, {str(now): now})                    # registrar request actual
        pipe.zcard(key)                                    # contar en la ventana
        pipe.expire(key, window_seconds)                   # TTL siempre presente
        results = await pipe.execute()

    current_count: int = results[2]
    allowed = current_count <= limit
    remaining = max(0, limit - current_count)
    return allowed, remaining

# Uso para tutor (por ejercicio):
# key = key_tutor_ratelimit(user_id, exercise_id)
# allowed, remaining = await check_rate_limit(redis, key, limit=30, window_seconds=3600)

# Uso para login (por IP):
# key = key_login_ratelimit(request.client.host)
# allowed, remaining = await check_rate_limit(redis, key, limit=10, window_seconds=300)
```

### 3. Token Blacklist con TTL = Vida Restante del Token

Al hacer refresh rotation, el token viejo se blacklistea hasta que expire naturalmente.

```python
# infrastructure/redis/token_blacklist.py

import time
from redis.asyncio import Redis
from app.infrastructure.redis.keys import key_token_blacklist

async def blacklist_token(redis: Redis, jti: str, exp: int) -> None:
    """
    Agrega el JTI a la blacklist con TTL igual al tiempo restante de vida del token.
    exp: timestamp de expiración del token (campo 'exp' del payload JWT).
    """
    ttl = int(exp - time.time())
    if ttl <= 0:
        return  # ya expiró, no hace falta blacklistear
    key = key_token_blacklist(jti)
    await redis.setex(key, ttl, "blacklisted")

async def is_token_blacklisted(redis: Redis, jti: str) -> bool:
    key = key_token_blacklist(jti)
    return await redis.exists(key) == 1
```

### 4. Redis Streams para Event Bus entre Fases

El event bus inter-fases usa **Redis Streams**, no Pub/Sub. Los Streams garantizan persistencia,
grupos de consumidores y acknowledgment. Pub/Sub es solo para multiplexing WS entre workers.

Streams canónicos: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`

```python
# infrastructure/redis/event_bus.py

import json
from redis.asyncio import Redis

# Streams canónicos del sistema
STREAM_SUBMISSIONS = "events:submissions"
STREAM_TUTOR       = "events:tutor"
STREAM_CODE        = "events:code"
STREAM_COGNITIVE   = "events:cognitive"

async def publish_event(
    redis: Redis,
    stream: str,
    payload: dict,
) -> str:
    """
    Publica un evento en el stream especificado.
    Retorna el ID del mensaje generado por Redis.
    Ejemplo: stream=STREAM_TUTOR, payload={"event_type": "interaction_saved", ...}
    """
    message_id = await redis.xadd(stream, {"data": json.dumps(payload)})
    return message_id

async def consume_events(
    redis: Redis,
    stream: str,
    group: str,
    consumer: str,
    count: int = 10,
) -> list[tuple[str, dict]]:
    """
    Consume eventos de un stream con consumer group.
    Retorna lista de (message_id, payload).
    El caller es responsable de hacer XACK después de procesar.
    """
    # Crear el grupo si no existe (MKSTREAM crea el stream si no existe)
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # el grupo ya existe

    messages = await redis.xreadgroup(
        groupname=group,
        consumername=consumer,
        streams={stream: ">"},  # ">" = solo mensajes no entregados
        count=count,
        block=5000,  # esperar hasta 5s si no hay mensajes
    )

    result = []
    if messages:
        for _, msgs in messages:
            for msg_id, data in msgs:
                payload = json.loads(data[b"data"])
                result.append((msg_id, payload))
    return result

async def ack_event(redis: Redis, stream: str, group: str, message_id: str) -> None:
    """Confirma el procesamiento de un evento (elimina del PEL)."""
    await redis.xack(stream, group, message_id)

# Ejemplo de consumidor Phase 3 (cognitive analytics):
# async def phase3_worker(redis: Redis) -> None:
#     while True:
#         events = await consume_events(redis, STREAM_COGNITIVE, "phase3", "worker-1")
#         for msg_id, payload in events:
#             await _handle_cognitive_event(payload)
#             await ack_event(redis, STREAM_COGNITIVE, "phase3", msg_id)
```

## Anti-patrones

### DON'T: Usar KEYS (bloquea el event loop en producción)

```python
# MAL — bloquea Redis por completo con millones de claves
keys = await redis.keys("ainative:cache:*")
```

```python
# BIEN — usar SCAN con cursor
async def scan_keys(redis: Redis, pattern: str) -> list[str]:
    keys = []
    cursor = 0
    while True:
        cursor, batch = await redis.scan(cursor, match=pattern, count=100)
        keys.extend(batch)
        if cursor == 0:
            break
    return keys
```

### DON'T: Crear claves sin TTL (memory leak garantizado)

```python
# MAL — clave que vive para siempre
await redis.set("ainative:cache:user:123", json.dumps(user_data))
```

```python
# BIEN — siempre TTL explícito
TTL_CACHE_USER = 300  # 5 minutos
await redis.setex(key_cache("user", user_id), TTL_CACHE_USER, json.dumps(user_data))
```

### DON'T: Concatenar strings para construir claves

```python
# MAL — propenso a errores, difícil de refactorizar
key = "rl:tutor:" + user_id + ":" + exercise_id
```

```python
# BIEN — siempre la builder function centralizada
key = key_tutor_ratelimit(user_id, exercise_id)
```

## Checklist

- [ ] Toda clave Redis usa la builder function correspondiente de `redis/keys.py`
- [ ] Toda clave nueva tiene TTL explícito definido como constante nombrada
- [ ] No hay ninguna llamada a `redis.keys()` en el codebase (usar `redis.scan()`)
- [ ] Rate limiter de tutor usa `key_tutor_ratelimit(user_id, exercise_id)`, `limit=30, window_seconds=3600`
- [ ] Rate limiter de login usa `key_login_ratelimit(ip)`, `limit=10, window_seconds=300`
- [ ] La blacklist de tokens usa `ttl = exp - now` (no TTL fijo)
- [ ] El event bus inter-fases usa Redis Streams (`xadd` / `xreadgroup` / `xack`)
- [ ] Pub/Sub solo se usa para multiplexing WS entre workers uvicorn (no para el event bus)
- [ ] Los streams canónicos son: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`
- [ ] Los pipelines se usan con `async with redis.pipeline(transaction=True)`
