# Consideraciones de Escalabilidad — Plataforma AI-Native

Análisis de capacidad, cuellos de botella y estrategias de escala para la plataforma.

---

## Estado actual (Piloto)

- **Usuarios**: 1 comisión (~30 alumnos simultáneos)
- **Infraestructura**: instancia única de cada servicio
- **Deployment**: Docker Compose en un solo host
- **Conclusión**: la configuración actual es suficiente para el piloto. No sobre-ingenierizar.

---

## Cuellos de botella identificados

### 1. Llamadas a la API de Anthropic (LLM)

**Problema**: cada interacción con el tutor es una llamada bloqueante a la API de Anthropic. El tiempo de respuesta depende de la carga del modelo (típicamente 2-10 segundos). El rate limit del tier gratuito/inicial es bajo.

**Impacto**: si 10 alumnos piden ayuda al tutor simultáneamente, los últimos esperan en cola.

**Mitigaciones**:
- Implementar cola de requests (Redis Queue / Celery) para serializar las llamadas al LLM
- Caché de respuestas para preguntas frecuentes (hash de la pregunta como key en Redis, TTL 1h)
- Fallback a Ollama local para preguntas no críticas (sintaxis básica, definiciones)
- Streaming de respuestas vía WebSocket para mejorar perceived performance

### 2. Ejecución de código en sandbox

**Problema**: cada submission ejecuta un subprocess de Python en un container aislado. La ejecución es secuencial por defecto.

**Impacto**: si 30 alumnos hacen submit simultáneamente, el último puede esperar varios minutos.

**Mitigaciones**:
- Pool de workers para ejecuciones concurrentes (N workers = N submissions simultáneas)
- Cola de ejecución en Redis con feedback de posición al alumno ("Posición en cola: 3")
- Timeout estricto por ejecución (máx 10 segundos de CPU) para evitar monopolización
- Límite de submissions por usuario por período (rate limiting a nivel de endpoint)

### 3. WebSocket con múltiples workers

**Problema**: uvicorn con múltiples workers crea procesos separados. Un WebSocket conectado a worker A no puede recibir eventos emitidos por worker B.

**Impacto**: notificaciones en tiempo real inconsistentes con más de 1 worker.

**Mitigaciones**:
- Sticky sessions en nginx (si hay múltiples API nodes)
- Redis Pub/Sub como bus de eventos entre workers: cada worker publica y suscribe al mismo canal
- Arquitectura preferida: 1 proceso dedicado de WebSocket gateway + múltiples workers de API REST

---

## Escalado horizontal de la API

La API FastAPI es **stateless** (excepto por WebSockets), lo que facilita el escalado horizontal.

```yaml
# docker-compose.prod.yml — múltiples workers en un proceso
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# O con gunicorn + uvicorn workers
command: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

**Regla de thumb para workers**: `(2 × núcleos_CPU) + 1`. Con 4 cores → 9 workers máx.

Para escala real (multi-host), agregar un load balancer (nginx o AWS ALB) delante de múltiples instancias de la API en contenedores separados.

---

## Base de datos

### Connection pooling

asyncpg ya usa connection pooling internamente. Configurar correctamente:

```python
# backend/app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # conexiones base en el pool
    max_overflow=10,       # conexiones adicionales bajo carga
    pool_timeout=30,       # tiempo máximo esperando una conexión libre
    pool_recycle=1800,     # reciclar conexiones cada 30 minutos
)
```

### Read replicas para analytics

El schema `analytics` tiene queries pesadas (agregaciones, reportes). Configurar una read replica de PostgreSQL y redirigir las queries del schema `analytics` a ella:

```python
# Conexión separada para analytics (read replica)
analytics_engine = create_async_engine(ANALYTICS_DB_URL, ...)
```

### Particionado de tablas

A largo plazo, particionar `governance.audit_logs` y `analytics.session_metrics` por rango de fecha (PARTITION BY RANGE) para mantener queries rápidas cuando los datos crezcan.

---

## Redis

### Uso actual

| Propósito | Key pattern | TTL |
|---|---|---|
| Caché de contexto del tutor | `tutor:ctx:{session_id}` | 1h |
| Rate limiting tutor | `rl:tutor:{user_id}:{exercise_id}` | 1h (sliding window) |
| Rate limiting login | `rl:login:{ip}` | 1min (sliding window) |
| Event bus entre fases | Redis Streams: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive` | — |
| Multiplexing WS entre workers | Canal Pub/Sub `ws:events` (solo WS worker, no inter-fase) | — |
| Blacklist de JWT | `jwt:blacklist:{jti}` | = expiración del token |

### Escalado de Redis

Para el piloto, un solo Redis es más que suficiente. Si el volumen crece:
- **Redis Sentinel**: alta disponibilidad (failover automático, sin escala de throughput)
- **Redis Cluster**: sharding automático para alto throughput (complica el Pub/Sub)

---

## Sandbox de ejecución de código

### Arquitectura actual (piloto)

```
Submission → API endpoint → subprocess.run(timeout=10) → resultado
```

### Arquitectura para escala

```
Submission → API → Redis Queue → Sandbox Workers (pool N) → resultado via WebSocket
```

Implementación sugerida:
1. `POST /api/v1/submissions` encola en Redis y devuelve `submission_id` + posición en cola
2. Pool de N workers toman submissions de la cola y ejecutan en Docker containers efímeros
3. Resultado publicado en Redis Pub/Sub → WebSocket gateway → cliente

---

## Triggers para escalar

Monitorear estas métricas y actuar cuando se superen los umbrales:

| Métrica | Umbral de alerta | Umbral crítico | Acción |
|---|---|---|---|
| Response time P95 de la API | > 1s | > 2s | Agregar workers / scale up |
| Error rate (5xx) | > 1% | > 5% | Investigar + rollback si necesario |
| Tiempo de respuesta del tutor | > 5s | > 10s | Activar cola + caché |
| Queue depth de submissions | > 10 | > 30 | Agregar sandbox workers |
| CPU del host | > 70% | > 85% | Scale up instancia o agregar nodo |
| Conexiones activas a DB | > 80% del pool | > 95% | Aumentar pool_size o agregar réplica |
| Uso de memoria Redis | > 70% maxmemory | > 85% | Aumentar memoria o revisar TTLs |

---

## Plan de escalado por etapa

| Etapa | Usuarios | Infraestructura | Cambio principal |
|---|---|---|---|
| Piloto | ~30 | Docker Compose, 1 host | — (configuración actual) |
| Expansión | ~150 | Docker Compose, 1 host potente | +workers API, cola de sandbox |
| Multi-comisión | ~300 | Docker Swarm o K8s básico | Redis Pub/Sub para WS worker multiplexing, Redis Streams para event bus, read replica DB |
| Institucional | 1000+ | K8s + managed DB (RDS) + managed Redis | CDN para frontend, DMS para migraciones |

---

## LLM: estrategia de fallback

Para garantizar disponibilidad cuando Anthropic tenga downtime o rate limiting:

```
Intento 1: Anthropic Claude (producción, calidad máxima)
     ↓ (si falla o timeout > 15s)
Intento 2: Ollama local con Llama 3 (fallback, calidad aceptable)
     ↓ (si Ollama no está disponible)
Intento 3: Respuesta pre-programada + "El tutor no está disponible temporalmente"
```

Implementar con circuit breaker pattern para no saturar un servicio caído.
