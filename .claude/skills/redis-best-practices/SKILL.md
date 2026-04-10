---
name: redis-best-practices
description: >
  Convenciones de naming de claves Redis, políticas de TTL, pub/sub para el event bus
  entre fases, rate limiting con sliding window y blacklist de tokens JWT.
  Trigger: cuando se trabaje con Redis — cache, event bus, rate limiting o gestión de tokens.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o acceder a cualquier clave Redis en el proyecto
- Al implementar rate limiting (tutor: 30 msg/hora, general: 100 req/min)
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
    RATELIMIT = "ratelimit"
    BLACKLIST = "blacklist"
    EVENTS   = "events"
    SESSION  = "session"

def key_cache(entity: str, entity_id: str) -> str:
    """ainative:cache:{entity}:{id}"""
    return f"ainative:{RedisDomain.CACHE}:{entity}:{entity_id}"

def key_ratelimit(user_id: str, endpoint: str) -> str:
    """ainative:ratelimit:{user_id}:{endpoint}"""
    return f"ainative:{RedisDomain.RATELIMIT}:{user_id}:{endpoint}"

def key_token_blacklist(jti: str) -> str:
    """ainative:blacklist:token:{jti}"""
    return f"ainative:{RedisDomain.BLACKLIST}:token:{jti}"

def key_event(source: str, event_type: str) -> str:
    """ainative:events:{source}:{event_type}"""
    return f"ainative:{RedisDomain.EVENTS}:{source}:{event_type}"

def key_session(user_id: str) -> str:
    """ainative:session:{user_id}"""
    return f"ainative:{RedisDomain.SESSION}:{user_id}"
```

### 2. Sliding Window Rate Limiter con Pipeline

Rate limits del proyecto: **30 msg/hora** para el tutor IA, **100 req/min** general.

```python
# infrastructure/redis/rate_limiter.py

import time
from redis.asyncio import Redis
from app.infrastructure.redis.keys import key_ratelimit

async def check_rate_limit(
    redis: Redis,
    user_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding window rate limiter. Retorna (allowed, remaining).
    Ejemplo: limit=30, window_seconds=3600 → tutor endpoint.
    """
    key = key_ratelimit(user_id, endpoint)
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

### 4. Pub/Sub para Event Bus entre Fases

Phase 1 (ingesta CTR) y Phase 2 (evaluación N4) publican eventos.
Phase 3 (análisis agregado) suscribe y procesa.

```python
# infrastructure/redis/event_bus.py

import json
from redis.asyncio import Redis
from app.infrastructure.redis.keys import key_event

async def publish_event(
    redis: Redis,
    source: str,
    event_type: str,
    payload: dict,
) -> None:
    """
    Publica un evento en el canal ainative:events:{source}:{event_type}.
    Ejemplo: source="ctr", event_type="hash_verified"
    """
    channel = key_event(source, event_type)
    await redis.publish(channel, json.dumps(payload))

async def subscribe_phase3(redis: Redis) -> None:
    """Consumidor de Phase 3: suscribe a eventos de ctr y evaluacion."""
    pubsub = redis.pubsub()
    await pubsub.psubscribe(
        key_event("ctr", "*"),
        key_event("evaluacion", "*"),
    )
    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue
        channel: str = message["channel"].decode()
        data: dict = json.loads(message["data"])
        await _handle_phase3_event(channel, data)

async def _handle_phase3_event(channel: str, data: dict) -> None:
    # Dispatcher por canal
    ...
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
key = "ainative:" + domain + ":" + user_id + ":" + endpoint
```

```python
# BIEN — siempre la builder function centralizada
key = key_ratelimit(user_id, endpoint)
```

## Checklist

- [ ] Toda clave Redis usa la builder function correspondiente de `redis/keys.py`
- [ ] Toda clave nueva tiene TTL explícito definido como constante nombrada
- [ ] No hay ninguna llamada a `redis.keys()` en el codebase (usar `redis.scan()`)
- [ ] Rate limiter de tutor usa `limit=30, window_seconds=3600`
- [ ] Rate limiter general usa `limit=100, window_seconds=60`
- [ ] La blacklist de tokens usa `ttl = exp - now` (no TTL fijo)
- [ ] Pub/Sub usa `psubscribe` con el patrón `key_event(source, "*")` para flexibilidad
- [ ] Los pipelines se usan con `async with redis.pipeline(transaction=True)`
- [ ] El channel de eventos sigue el patrón `ainative:events:{source}:{event_type}`
