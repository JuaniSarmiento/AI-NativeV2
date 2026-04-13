# 07 — Architecture Decision Records (ADRs)

**Plataforma AI-Native — UTN FRM — Documentación de Arquitectura**
**Versión:** 1.0 | **Estado:** Vigente | **Formato:** MADR (Markdown Any Decision Records)

---

## Tabla de Contenidos

- [Sobre este documento](#sobre-este-documento)
- [ADR-001: Monolito Modular sobre Microservicios](#adr-001-monolito-modular-sobre-microservicios)
- [ADR-002: Hash Chain SHA-256 para Integridad del CTR](#adr-002-hash-chain-sha-256-para-integridad-del-ctr)
- [ADR-003: WebSocket Streaming para el Tutor IA](#adr-003-websocket-streaming-para-el-tutor-ia)
- [ADR-004: Event Bus para Comunicación entre Fases](#adr-004-event-bus-para-comunicación-entre-fases)
- [ADR-005: Sandbox para Ejecución de Código de Estudiantes](#adr-005-sandbox-para-ejecución-de-código-de-estudiantes)
- [ADR-006: Múltiples Adaptadores LLM con Protocolo Invariante](#adr-006-múltiples-adaptadores-llm-con-protocolo-invariante)
- [ADR-007: Cuatro Schemas de PostgreSQL para Aislamiento de Datos](#adr-007-cuatro-schemas-de-postgresql-para-aislamiento-de-datos)
- [Registro de Cambios](#registro-de-cambios)

---

## Sobre este documento

Las Architecture Decision Records (ADRs) documentan las decisiones arquitectónicas significativas tomadas durante el desarrollo de la plataforma AI-Native. Cada ADR captura:

- **El contexto** en el que se tomó la decisión (fuerzas en juego, restricciones, requisitos).
- **La decisión tomada** y su justificación.
- **Las consecuencias** esperadas (positivas y negativas).
- **Las alternativas consideradas** y por qué fueron descartadas.

Estas decisiones son especialmente importantes en el contexto de la tesis doctoral, ya que documentan el razonamiento detrás de elecciones de diseño que afectan la validez metodológica del experimento.

### Estados posibles de un ADR

| Estado | Significado |
|--------|-------------|
| **Propuesto** | En discusión, no implementado |
| **Aceptado** | Implementado y vigente |
| **Deprecado** | Fue aceptado pero ya no aplica |
| **Reemplazado** | Reemplazado por otro ADR (indica cuál) |

---

## ADR-001: Monolito Modular sobre Microservicios

**Fecha:** 2026-01-15
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Alto — define la topología de despliegue de toda la plataforma

---

### Contexto

El proyecto AI-Native es desarrollado por un equipo de cuatro desarrolladores (un director de tesis + tres investigadores/desarrolladores) en el marco de un proyecto de investigación universitaria. El dominio del problema tiene alta complejidad intrínseca: clasificación cognitiva con IA, cadena de hash para trazabilidad, streaming de LLM, sandbox de ejecución de código.

**Fuerzas en juego:**

1. **Complejidad de dominio vs. complejidad de infraestructura**: La complejidad real del sistema reside en los algoritmos (N4 classification, CTR hash chain, Socratic pedagogy en prompts), no en el tráfico o la escala.

2. **Tamaño del equipo**: Con cuatro desarrolladores, el overhead de operar múltiples servicios independientes (CI/CD por servicio, service discovery, distributed tracing, circuit breakers) consumiría una fracción significativa del tiempo de desarrollo.

3. **Contexto universitario**: La plataforma debe funcionar en el data center de UTN FRM, que no tiene infraestructura de Kubernetes ni orquestación de contenedores sofisticada.

4. **Requisito de tesis**: Los experimentos deben ser reproducibles. Un sistema simpler de deployar aumenta la posibilidad de que otros investigadores puedan replicar el entorno.

5. **Crecimiento esperado**: La base de usuarios esperada es de 30-300 estudiantes concurrentes (una o varias aulas de la carrera). No hay proyección de escala a miles de usuarios en el horizonte de la tesis.

**Tensiones principales:**

- Los módulos (fases 1, 2, 3, 4) tienen datos relacionados pero ownership diferente.
- Se necesita desacoplamiento conceptual sin necesitar desacoplamiento de despliegue.
- El equipo necesita poder hacer deployar todo el sistema en un solo comando.

---

### Decisión

**Implementar un monolito modular** (también conocido como "modular monolith" o "single deployable unit with internal boundaries").

La arquitectura consiste en:
- **Un único proceso Python** (FastAPI + uvicorn) que contiene todos los módulos.
- **Módulos internos con fronteras explícitas**: `phase1`, `phase2`, `phase3`, `phase4`, `shared`.
- **Cuatro schemas de PostgreSQL** que actúan como límites de datos (ver ADR-007).
- **Comunicación entre módulos** exclusivamente via event bus (ver ADR-004) o llamadas REST internas a los propios endpoints del monolito.
- **Un único repositorio de código** (monorepo) con frontend y backend.

La separación es **conceptual y de ownership**, no de despliegue.

```
[ Single Process: FastAPI App ]
├── features/auth        → router → service → repo → operational.*
├── features/courses     → router → service → repo → operational.*
├── features/exercises   → router → service → repo → operational.*
├── features/sandbox     → router → service → (subprocess)
├── features/tutor       → router → service → repo → operational.* + LLM API
├── features/cognitive   → router → service → repo → cognitive.*
├── features/evaluation  → router → service → repo → cognitive.*
├── features/governance  → router → service → repo → governance.* + analytics.*
└── shared               → db, models, repositories, exceptions, event bus, LLM adapters
```

---

### Consecuencias

**Positivas:**

- **Despliegue simple**: `docker compose up` levanta toda la plataforma. Un solo Dockerfile para el backend.
- **Debugging simplificado**: Un solo proceso, un solo log stream, un solo stack trace. No hay network hops entre servicios.
- **Transacciones locales**: Cuando una operación necesita datos de múltiples módulos en la misma transacción (ej: crear submission + emitir evento), se puede hacer en una sola transacción PostgreSQL.
- **Refactoring más fácil**: Mover código entre módulos es una operación local sin tocar contratos de red.
- **Menor latencia interna**: Las llamadas entre módulos son llamadas de función o llamadas HTTP a localhost, no network calls entre contenedores.
- **Sin distributed tracing overhead**: No se necesita Jaeger, Zipkin, etc. para el contexto de tesis.

**Negativas / Riesgos:**

- **Escalado por módulo es imposible**: Si Phase 2 (tutor) necesita más CPU por el LLM streaming, no se puede escalar solo ese módulo. Hay que escalar todo el proceso.
- **Fallo compartido**: Un bug de memoria en Phase 3 puede afectar a Phase 1. Mitigación: unit tests estrictos, linting, revisión de código.
- **Fronteras de módulo se pueden erosionar**: Los desarrolladores pueden sentir la tentación de importar directamente de otro módulo. Mitigación: linter personalizado que verifica imports cross-module.
- **Deployment monolítico**: Un cambio en Phase 4 requiere desplegar todo el sistema. Para el contexto universitario esto es aceptable.

**Neutrales:**

- La decisión no cierra la puerta a una migración futura a microservicios. Los límites de módulo están bien definidos y los contratos REST ya existen. Si el sistema crece, la extracción es directa.

---

### Alternativas Consideradas

**Opción A: Microservicios desde el inicio**
- 4 servicios independientes, uno por fase.
- *Rechazada*: overhead de infraestructura (service mesh, API gateway, distributed config, distributed tracing) excede en complejidad a los beneficios para un equipo de 4 personas y 300 usuarios máximos.

**Opción B: Dos servicios (backend + worker)**
- Backend HTTP + worker async separado para procesamiento de eventos.
- *Considerada como evolución futura*: El worker de Phase 3 (clasificación cognitiva) es un candidato natural para extracción si el procesamiento se vuelve CPU-intensive.

**Opción C: Serverless (AWS Lambda)**
- *Rechazada*: Los WebSockets de larga duración para streaming LLM son incompatibles con el modelo stateless de Lambda. Además, el contexto universitario no garantiza acceso a AWS.

---

## ADR-002: Hash Chain SHA-256 para Integridad del CTR

**Fecha:** 2026-01-20
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Crítico — afecta la validez metodológica de la tesis

---

### Contexto

El **Cognitive Trace Record (CTR)** es el registro central de evidencia de la tesis doctoral. Captura cada evento cognitivo del estudiante durante sus sesiones de aprendizaje: qué preguntó al tutor, cuándo ejecutó código, cuántos errores cometió, cómo progresó su clasificación N4.

**El problema central**: ¿Cómo garantizar que los datos del CTR no fueron alterados post-hoc? En una tesis doctoral, la integridad de los datos experimentales es fundamental. Un revisor externo o comité evaluador debe poder verificar que los registros no fueron modificados para confirmar la hipótesis.

**Requisitos:**

1. Los eventos del CTR deben ser **append-only**: una vez registrado un evento, no puede modificarse ni eliminarse.
2. Debe ser posible verificar la integridad del registro completo en cualquier momento.
3. La verificación debe ser independiente: cualquier persona con acceso a los datos debe poder verificarla sin confiar en el sistema que los generó.
4. El mecanismo no debe agregar latencia significativa al flujo del estudiante.

**Restricción adicional**: El sistema debe funcionar sin blockchain (demasiado complejo para el scope de la tesis) pero con garantías matemáticamente verificables.

---

### Decisión

**Implementar una cadena de hash SHA-256 por sesión cognitiva**, inspirada en el mecanismo de cadena de bloques pero sin consenso distribuido.

**Mecanismo:**

Cada entrada del CTR contiene:
```
entry_hash = SHA-256(
    previous_hash ||    # Hash de la entrada anterior (o genesis_hash si es la primera)
    event_type ||
    payload_json ||     # serializado con claves ordenadas
    created_at_iso8601
)
```

El genesis hash de cada sesión se calcula como:
```
genesis_hash = SHA-256("GENESIS:" + session_id + ":" + started_at.isoformat())
```

Esto garantiza que el genesis hash es único por sesión.

**Verificación de integridad:**

```python
# app/features/cognitive/services/ctr_integrity.py

import hashlib
import json
from app.features.cognitive.repositories.ctr_repo import CTRRepository


class CTRIntegrityVerifier:
    """
    Verifica que la cadena de hash del CTR no fue alterada.

    Algoritmo:
    1. Cargar todas las entradas de la sesión ordenadas por created_at ASC.
    2. Para cada entrada, recalcular el hash esperado.
    3. Comparar con el hash almacenado.
    4. Si algún hash no coincide, la cadena fue comprometida.
    """

    async def verify_session(self, session_id: str) -> VerificationResult:
        entries = await self._repo.get_session_entries_ordered(session_id)

        if not entries:
            return VerificationResult(valid=True, entries_checked=0)

        # El genesis hash se computa como SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())
        # y está almacenado en cognitive_sessions.genesis_hash
        previous_hash = session.genesis_hash

        for i, entry in enumerate(entries):
            expected_hash = self._compute_hash(
                previous_hash=previous_hash,
                event_type=entry.event_type,
                payload=entry.payload,
                created_at=entry.created_at.isoformat(),
            )

            if expected_hash != entry.entry_hash:
                return VerificationResult(
                    valid=False,
                    entries_checked=i + 1,
                    first_violation_index=i,
                    expected_hash=expected_hash,
                    stored_hash=entry.entry_hash,
                )

            previous_hash = entry.entry_hash

        return VerificationResult(valid=True, entries_checked=len(entries))

    @staticmethod
    def _compute_hash(
        previous_hash: str,
        event_type: str,
        payload: dict,
        created_at: str,
    ) -> str:
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        data = f"{previous_hash}:{event_type}:{payload_str}:{created_at}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
```

---

### Consecuencias

**Positivas:**

- **Verificabilidad matemática**: Cualquier alteración en cualquier campo de cualquier entrada invalida todos los hashes subsiguientes, haciendo la manipulación detectable.
- **Sin dependencias externas**: No requiere blockchain, timestamp authority, ni ningún servicio externo.
- **Trazabilidad completa**: El orden temporal de los eventos es parte del hash (el timestamp está incluido), por lo que tampoco se puede reordenar la secuencia.
- **Exportable**: Los datos del CTR con sus hashes pueden exportarse a CSV/JSON y verificarse con cualquier implementación de SHA-256 estándar, sin necesitar el software de la plataforma.

**Negativas / Riesgos:**

- **Append-only estricto**: No se puede corregir un error en una entrada registrada sin invalidar toda la cadena subsiguiente. Si un bug del sistema registra un evento erróneo, hay que documentarlo pero no corregirlo (o re-computar toda la cadena, lo cual es una operación auditada).
- **Latencia de escritura mínima**: Cada nueva entrada del CTR debe esperar a que la entrada anterior esté confirmada en DB antes de poder computar su hash (no se pueden escribir en paralelo dentro de la misma sesión). El impacto es < 5ms por entrada dado que son operaciones locales a PostgreSQL.
- **Sesiones no pueden correr en paralelo**: Dos eventos de la misma sesión cognitiva no pueden registrarse concurrentemente (violaría la cadena). Se maneja con un lock optimista a nivel de sesión.
- **SHA-256 no es resistente a quantum computing**: Para el horizonte de la tesis (5 años), este riesgo es teórico. Si la plataforma se usa a largo plazo, migrar a SHA-3.

**Neutrales:**

- La cadena solo provee integridad, no confidencialidad. Los datos del CTR son legibles por cualquiera con acceso a la DB. Si se requiere privacidad del estudiante, hay que aplicar cifrado en reposo por separado (fuera del scope del ADR).

---

### Alternativas Consideradas

**Opción A: Firma digital por entrada (RSA/Ed25519)**
- Cada entrada firmada con clave privada del servidor.
- *Rechazada*: La clave privada está en el mismo sistema que los datos. Si el servidor es comprometido, las firmas también lo son. No agrega más garantía que el hash chain para el modelo de amenaza de la tesis.

**Opción B: Blockchain pública (Ethereum/Polygon)**
- Publicar hash raíz de la cadena en blockchain pública.
- *Rechazada*: Overhead de costo (gas fees), complejidad de integración, y requiere wallet management. Para el scope de tesis académica, es sobreingeniería.

**Opción C: Tabla inmutable en PostgreSQL (row-level security sin DELETE)**
- Usar PostgreSQL policies para prohibir DELETE y UPDATE.
- *Adoptada como complemento*: Se usa junto con el hash chain. El hash chain provee verificabilidad matemática; las policies de PostgreSQL proveen una capa adicional de protección contra modificaciones accidentales.

---

## ADR-003: WebSocket Streaming para el Tutor IA

**Fecha:** 2026-01-22
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Alto — define la experiencia del usuario en el módulo más visible

---

### Contexto

El tutor IA usa modelos de lenguaje grandes (LLM) como Claude de Anthropic. Estos modelos generan respuestas de forma autoregressiva: producen un token a la vez. Una respuesta típica del tutor puede tener entre 100 y 500 tokens (50-250 palabras), lo que a una velocidad de generación de ~30-60 tokens/segundo tarda entre 2 y 15 segundos en completarse.

**El problema de UX**: Si el frontend espera la respuesta completa antes de mostrarla, el estudiante ve un spinner durante 2-15 segundos y luego de golpe aparece todo el texto. Esto es:
- Perceptivamente lento (el estudiante no sabe si el sistema está procesando).
- Menos natural que una conversación humana (donde escuchás las palabras a medida que se pronuncian).
- Aumenta la tasa de abandono de la sesión tutora.

**Requisitos del streaming:**
1. El primer token debe aparecer en pantalla en < 500ms desde que el estudiante envía su mensaje.
2. La conexión debe mantenerse mientras el estudiante está en la sesión de ejercicio (potencialmente 30-60 minutos).
3. El protocolo debe permitir mensajes bidireccionales (el tutor puede necesitar solicitar aclaraciones).
4. La autenticación debe ser segura pero compatible con las restricciones del protocolo WebSocket en navegadores.

---

### Decisión

**Usar WebSocket (RFC 6455) con streaming token a token** para la comunicación entre el frontend y el backend del tutor.

**Detalles de implementación:**

- **Endpoint**: `wss://api.ai-native.edu/ws/tutor/chat`
- **Autenticación**: JWT en query parameter `?token=<jwt>` (ver justificación en la sección de consecuencias).
- **Protocolo de mensajes**:
  - Cliente → Servidor: `{ type: "message", payload: { content: string, current_code: string } }`
  - Servidor → Cliente (tokens): `{ type: "token", payload: { text: string } }`
  - Servidor → Cliente (final): `{ type: "complete", payload: { classification_n4: "N1"|"N2"|"N3"|"N4" } }`
  - Servidor → Cliente (heartbeat): `{ type: "ping" }`
  - Cliente → Servidor (heartbeat): `{ type: "pong" }`
- **Heartbeat**: ping del servidor cada 30 segundos; si no recibe pong en 10s, cierra con código 1011.
- **Reconexión cliente**: backoff exponencial (1s, 2s, 4s, 8s, ..., máx 30s) con jitter ±20%.

**Justificación del JWT en query param:**

La API WebSocket del navegador (`new WebSocket(url)`) no permite configurar headers HTTP custom en el handshake. Las alternativas son:
1. JWT en query param (elegida): simple, funciona en todos los navegadores, el riesgo de log exposure se mitiga con TLS y exclusión de `/ws/` de access logs.
2. Cookie HttpOnly (alternativa descartada): requiere configuración CORS compleja y no funciona con el flujo de renovación de tokens existente.
3. Subprotocolo de autenticación post-handshake: el cliente envía el token como primer mensaje tras conectar, antes de cualquier chat. Se puede agregar como mejora de seguridad si es necesario.

---

### Consecuencias

**Positivas:**

- **UX conversacional fluida**: El primer token aparece en < 100ms (latencia de red + generación del primer token del LLM). El estudiante ve la respuesta construirse en tiempo real.
- **Reducción de TTFB percibida**: Incluso si la respuesta tarda 8 segundos en completarse, el estudiante ya leyó los primeros 50 tokens a los 2 segundos.
- **Bidireccionalidad**: El protocolo WebSocket permite al backend enviar eventos al frontend sin que el frontend lo solicite (notificaciones de clasificación N4, alertas del docente).
- **Una conexión por sesión**: Más eficiente que hacer un request HTTP por cada token.

**Negativas / Riesgos:**

- **Gestión de estado de conexión**: El frontend necesita manejar reconexión, timeouts, y el caso en que el stream sea interrumpido a mitad de una respuesta. La lógica de reconexión es no trivial (backoff, renovación de token, restauración de estado).
- **JWT en query param en logs**: Aunque mitigable con TLS y log masking, es una superficie de exposición mayor que un header HTTP. En la práctica, para el contexto universitario con infraestructura controlada, el riesgo es aceptable.
- **Incompatibilidad con algunos proxies corporativos**: Algunos proxies HTTP (especialmente en entornos empresariales con deep packet inspection) bloquean o degradan WebSockets. En entorno universitario con red controlada, esto no es un problema.
- **Conexiones idle**: Si el estudiante deja el tab abierto sin interactuar, la conexión WebSocket consume recursos del servidor. El heartbeat detecta y cierra conexiones zombie.
- **Manejo de estado en el frontend con React refs**: El WebSocket no puede vivir en el estado de React (re-renders cerrarían la conexión). Se requiere usar `useRef` para la instancia del WebSocket, lo que agrega complejidad al hook.

**Neutrales:**

- El servidor necesita ser async (uvicorn/asyncio). FastAPI con asyncio es la elección natural y ya estaba planificada.

---

### Alternativas Consideradas

**Opción A: Server-Sent Events (SSE)**
- HTTP/1.1 one-way push del servidor al cliente.
- *Rechazada*: SSE es unidireccional (servidor → cliente). Para enviar el mensaje del estudiante se necesitaría un request HTTP separado. La experiencia es discontínua y el estado de la conversación más complejo de manejar.

**Opción B: HTTP long polling**
- Cliente hace GET y espera; servidor responde cuando hay datos; cliente hace GET inmediatamente.
- *Rechazada*: Latencia mayor (overhead de TCP handshake en cada poll), más carga en el servidor, y la experiencia de streaming no es nativa.

**Opción C: HTTP streaming con Transfer-Encoding: chunked**
- Un único POST que retorna chunks a medida que el LLM genera tokens.
- *Considerada*: Más simple de implementar, no requiere gestión de reconexión. *Rechazada* porque no es verdaderamente bidireccional y algunos proxies/CDNs bufferean la respuesta antes de enviarla al cliente, destruyendo la experiencia de streaming.

---

## ADR-004: Event Bus para Comunicación entre Fases

**Fecha:** 2026-01-25
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Alto — define cómo Fase 3 consume información de Fases 1 y 2

---

### Contexto

La Fase 3 (clasificación cognitiva y CTR) necesita conocer eventos que ocurren en Fase 1 (ejecuciones de código, submissions) y Fase 2 (interacciones con el tutor). Hay tres formas en que esto puede ocurrir:

1. **Llamada directa de función**: Fase 1 llama directamente a `phase3_service.classify(...)` al completar una ejecución.
2. **Llamada HTTP síncrona**: Fase 1 hace un POST a `/api/v1/phase3/events` al completar una ejecución.
3. **Mensajería asíncrona**: Fase 1 publica un evento y Fase 3 lo consume de forma independiente.

**El problema con las opciones 1 y 2 (síncrono):**

Si la clasificación cognitiva falla o tarda (ej: la IA tarda 2 segundos en clasificar un evento), **el estudiante espera**. El flujo de ejecución de código quedaría bloqueado esperando que Fase 3 procese. Esto es inaceptable para la UX.

Además, si Fase 3 tiene un bug y crashea, **arrastraría a Fases 1 y 2 con él** si están acopladas síncronamente.

**Requisito fundamental**: Fases 1 y 2 no deben verse afectadas en latencia ni disponibilidad por el comportamiento de Fase 3.

---

### Decisión

**Implementar un Event Bus asíncrono basado en Redis Streams con consumer groups y tabla outbox en PostgreSQL como garantía de at-least-once delivery**.

**Streams Redis:**
```
events:submissions           → eventos de submission de ejercicios
events:tutor                 → eventos de interacción con el tutor
events:code                  → eventos de ejecución y snapshot de código
events:cognitive             → eventos cognitivos (consumido por analytics-group)
```

**Patrón dual:**
- Redis Streams con consumer groups: at-least-once delivery, baja latencia (< 5ms), persistencia y replay. Para la mayoría de los eventos.
- Tabla `operational.event_outbox`: persistencia en PostgreSQL, garantía transaccional. Para eventos críticos que no pueden perderse (CTR entries).

**Worker de Fase 3:**
- Consumer group en Redis Streams (`cognitive-group`) para procesamiento en tiempo real.
- Polling de outbox cada 5 segundos para eventos no procesados (fallback).
- Ambos corren como tasks asyncio dentro del mismo proceso.

---

### Consecuencias

**Positivas:**

- **Desacoplamiento temporal**: Fases 1 y 2 publican eventos y continúan sin esperar a Fase 3.
- **Resiliencia**: Si Fase 3 tiene downtime (ej: crash por bug), los eventos se acumulan en el outbox y son procesados cuando Fase 3 se recupera. No se pierde información.
- **Procesamiento a ritmo propio**: Fase 3 puede procesar a su velocidad sin crear backpressure en Fases 1 y 2.
- **Auditabilidad**: La tabla outbox es un registro histórico de todos los eventos del sistema, valioso para debugging y análisis post-hoc de la tesis.

**Negativas / Riesgos:**

- **Consistencia eventual**: Hay un delay entre que ocurre un evento y que Fase 3 lo clasifica. En la práctica < 100ms via Redis, o < 5s via outbox. Para el uso case (clasificación cognitiva para tesis), esto es completamente aceptable.
- **Complejidad del outbox**: La tabla outbox requiere un worker de polling y lógica de retry con backoff. Es más código que una llamada directa.
- **Riesgo de acumulación**: Si Fase 3 está caída por horas y hay muchos estudiantes activos, el outbox puede acumular miles de eventos. Requiere monitoreo del tamaño del outbox.
- **Orden de eventos entre streams**: Redis Streams garantiza orden dentro de un stream, pero no entre streams distintos. Para el CTR, el orden se determina por el timestamp de la entrada, no por el orden de llegada al worker.

---

### Alternativas Consideradas

**Opción A: Llamada síncrona directa (importar phase3 desde phase1)**
- *Rechazada*: Acoplamiento fuerte, latencia del tutor/ejecución afectada por clasificación, violación de fronteras de módulo.

**Opción B: Apache Kafka**
- Broker de mensajes con durabilidad, ordering, consumer groups.
- *Rechazada*: Overhead de operación (Zookeeper/KRaft, brokers, topic management) excede el scope del proyecto universitario. Redis ya es una dependencia del sistema (para caché y sesiones); reutilizarlo para Streams es más pragmático.

**Opción C: RabbitMQ**
- AMQP broker con colas durables, acks, dead-letter queues.
- *Rechazada*: Misma razón que Kafka. Redis Streams + outbox cubre el 95% de los requisitos sin dependencias adicionales.

**Opción D: Solo tabla outbox (sin Redis)**
- Polling puro, sin Streams.
- *Descartada como opción principal*: El polling con intervalo de 5s introduce latencia innecesaria en la clasificación cognitiva. Para datos de tesis donde el tiempo de clasificación puede ser relevante, preferimos Redis para el 99% de los eventos y outbox solo como garantía.

---

## ADR-005: Sandbox para Ejecución de Código de Estudiantes

**Fecha:** 2026-02-01
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Crítico — seguridad del servidor

---

### Contexto

La plataforma permite a los estudiantes escribir y ejecutar código Python arbitrario. **El código de los estudiantes es input no confiable**. Un estudiante (malicioso o simplemente curioso) puede intentar:

- Leer archivos del sistema (`/etc/passwd`, claves SSH, variables de entorno con secrets).
- Hacer llamadas de red (exfiltrar datos, escanear la red interna).
- Consumir recursos indefinidamente (loop infinito, fork bomb, consumo masivo de RAM).
- Escribir archivos en el sistema de archivos del servidor.
- Importar módulos del sistema operativo para ejecutar comandos (`os.system`, `subprocess`).

**Restricciones del contexto:**
- La plataforma corre en un servidor universitario con presupuesto limitado. No se dispone de infraestructura de contenedores gestionada (EKS, GKE).
- Los ejercicios son exclusivamente en Python para la versión inicial de la tesis.
- El tiempo de ejecución aceptable para un ejercicio de algoritmos básicos es < 5 segundos en condiciones normales.

---

### Decisión

**Implementar sandbox de ejecución con tres capas de protección:**

**Capa 1: timeout estricto (10 segundos)**

```python
# app/features/sandbox/services/code_executor.py

import subprocess
import resource

async def execute_code(code: str, stdin: str = "") -> ExecutionResult:
    result = await asyncio.wait_for(
        _run_subprocess(code, stdin),
        timeout=10.0,  # Hard timeout
    )
    return result
```

**Capa 2: límite de memoria (128 MB)**

```python
def set_memory_limit():
    """Llamado via preexec_fn en subprocess para limitar memoria."""
    # 128 MB = 128 * 1024 * 1024 bytes
    resource.setrlimit(
        resource.RLIMIT_AS,
        (128 * 1024 * 1024, 128 * 1024 * 1024)
    )

# En runtime async, usar asyncio.create_subprocess_exec (NUNCA subprocess.Popen síncrono)
process = await asyncio.create_subprocess_exec(
    "python3", "-c", sanitized_code,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    stdin=asyncio.subprocess.PIPE,
    preexec_fn=set_memory_limit,
    # Sin acceso a red (configurado a nivel de Docker network en producción)
)
```

**Capa 3: seccomp profile en Docker (producción)**

En producción, el contenedor del ejecutor corre con un perfil seccomp que bloquea syscalls de red (`socket`, `connect`, `bind`) y filesystem (`open` a directorios fuera de `/tmp`).

**Para la versión de tesis (desarrollo/lab):**
- Capas 1 y 2 son suficientes para el modelo de amenaza universitario.
- El código corre en un proceso Python hijo con stdin/stdout piped.
- No hay acceso a red (restricción de iptables en el servidor universitario).
- El proceso hijo se mata automáticamente si excede el timeout o la memoria.

---

### Consecuencias

**Positivas:**

- **Protección contra DoS básico**: loops infinitos y consumo de RAM están limitados.
- **Sin infraestructura adicional**: No requiere Docker-in-Docker, gVisor, ni Firecracker para el scope de tesis.
- **Simplicidad de implementación**: `subprocess + resource.setrlimit + asyncio.wait_for` son APIs estándar de Python.

**Negativas / Riesgos:**

- **Solo Python**: La restricción a un intérprete Python limita los ejercicios a ese lenguaje. Para agregar JavaScript, Go, etc., se necesita una arquitectura más compleja (contenedores por lenguaje).
- **Acceso limitado al filesystem**: El código del estudiante no puede importar archivos de datos del ejercicio directamente; deben ser pasados via stdin o hardcodeados.
- **setrlimit no disponible en Windows**: El servidor debe ser Linux. En el contexto universitario (servidor UTN FRM), esto es garantizado.
- **Bypass potencial via C extensions**: Módulos como `ctypes` pueden hacer syscalls directas. Mitigación: blacklist de imports en el analyzer de código (capa adicional a implementar en producción).

**Neutrales:**

- El timeout de 10 segundos es conservador para ejercicios de algoritmos básicos (loops, recursión, estructuras de datos). Los ejercicios de la tesis están diseñados para completarse en < 2 segundos en condiciones normales.

---

### Alternativas Consideradas

**Opción A: Docker por ejecución (docker run por submission)**
- Cada ejecución en un contenedor Docker efímero.
- *Rechazada para v1*: Overhead de ~500ms por contenedor launch. Viable para producción a futuro.

**Opción B: gVisor (runsc)**
- Kernel en espacio de usuario para aislamiento fuerte.
- *Rechazada*: Requiere soporte a nivel de kernel/docker daemon. No disponible en el servidor universitario actual.

**Opción C: WebAssembly (Pyodide)**
- Ejecutar Python en WASM en el navegador del estudiante.
- *Rechazada*: El código corre en el navegador, no en el servidor. No se puede garantizar el entorno de ejecución (diferentes versiones de Pyodide, performance variable). Además, los test cases con I/O son más complejos de manejar.

---

## ADR-006: Múltiples Adaptadores LLM con Protocolo Invariante

**Fecha:** 2026-02-05
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Alto — validez metodológica de los experimentos de la tesis

---

### Contexto

La tesis doctoral tiene como uno de sus objetivos comparar el comportamiento del tutor IA bajo diferentes modelos de lenguaje. La hipótesis experimental es que el **framework pedagógico socrático** (capturado en los prompts del sistema y el flujo de la conversación) produce resultados de aprendizaje superiores independientemente del LLM subyacente.

Para validar esta hipótesis, la plataforma debe poder:
1. Cambiar el LLM del tutor (Anthropic Claude, OpenAI GPT-4, Ollama local) sin cambiar el comportamiento de la aplicación.
2. Garantizar que cualquier diferencia en los resultados de aprendizaje se debe al LLM y no a diferencias en la integración técnica.
3. Ejecutar los mismos tests de validación contra todos los adaptadores.

**Restricción adicional**: La plataforma debe poder correr en modo offline con Ollama (para experimentos en entornos sin internet, como exámenes presenciales en el aula universitaria).

---

### Decisión

**Implementar el patrón de adaptador basado en Protocol de Python**, con tests de conformidad que garantizan invarianza de comportamiento entre todos los adaptadores.

El protocolo `LLMAdapter` define exactamente dos métodos:
- `complete(messages, *, system, max_tokens, temperature) → LLMResponse`
- `stream(messages, *, system, max_tokens, temperature) → AsyncIterator[LLMStreamChunk]`

Los tres adaptadores implementan el protocolo:
- `AnthropicAdapter`: usa `anthropic` SDK.
- `OpenAIAdapter`: usa `openai` SDK.
- `OllamaAdapter`: usa HTTP REST de Ollama (no SDK oficial, REST nativo).

**La invarianza se verifica mediante conformity tests** que corren automáticamente en CI contra los tres adaptadores, verificando:
- La respuesta no es vacía.
- El stream produce al menos un chunk y termina con `is_final=True`.
- La información de uso de tokens está presente en el chunk final.
- El modelo retorna su nombre correctamente.

**Configuración del adaptador activo:**

```python
# app/config.py

class Settings(BaseSettings):
    LLM_PROVIDER: Literal["anthropic", "openai", "ollama"] = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

# app/shared/llm/factory.py

def create_llm_adapter(settings: Settings) -> LLMAdapter:
    match settings.LLM_PROVIDER:
        case "anthropic":
            return AnthropicAdapter(model=settings.LLM_MODEL)
        case "openai":
            return OpenAIAdapter(model=settings.LLM_MODEL)
        case "ollama":
            return OllamaAdapter(
                model=settings.LLM_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
        case _:
            raise ValueError(f"LLM provider desconocido: {settings.LLM_PROVIDER}")
```

---

### Consecuencias

**Positivas:**

- **Cambio de LLM sin cambio de código**: Solo requiere cambiar la variable de entorno `LLM_PROVIDER`.
- **Validez experimental**: Los tests de conformidad garantizan que el comportamiento es equivalente entre adaptadores, lo que fortalece la validez interna de los experimentos.
- **Modo offline**: Con Ollama, la plataforma puede correr completamente sin internet.
- **Extensibilidad**: Agregar un nuevo proveedor (Gemini, Mistral) solo requiere implementar el protocolo y agregar al factory.

**Negativas / Riesgos:**

- **Mínimo común denominador**: El protocolo expone solo los parámetros comunes a todos los LLMs. Features específicos de un proveedor (ej: Anthropic's extended thinking, OpenAI's function calling) no están disponibles a través del adaptador genérico.
- **Tests de conformidad requieren API keys**: Los conformity tests contra Anthropic y OpenAI consumen tokens de las APIs. En CI, se usan mocks excepto en runs programados semanales.
- **Calidad diferente entre LLMs**: Aunque el protocolo es invariante, la *calidad* de las respuestas del tutor varía. Un estudiante puede tener mejor o peor experiencia según el LLM configurado. Esto es esperado y es parte del experimento de tesis.

---

### Alternativas Consideradas

**Opción A: Clase abstracta Python (ABC)**
- `class LLMAdapter(ABC): @abstractmethod def complete(...)`
- *Descartada en favor de Protocol*: Protocol permite duck typing y no requiere que los adaptadores hereden de la clase base. Más flexible para integrar con SDKs de terceros que tienen su propio modelo de herencia.

**Opción B: LangChain / LlamaIndex**
- Frameworks que abstraen múltiples LLMs.
- *Rechazada*: Dependencia grande con su propio modelo de abstracciones y bugs. Para el scope de la tesis, preferimos control total sobre la integración con el LLM (especialmente para el streaming token a token que es crítico para la UX).

---

## ADR-007: Cuatro Schemas de PostgreSQL para Aislamiento de Datos

**Fecha:** 2026-02-10
**Estado:** Aceptado
**Autores:** Equipo de arquitectura AI-Native
**Impacto:** Alto — define ownership de datos y governance de la DB

---

### Contexto

Cuatro fases del proyecto se desarrollan en paralelo por subequipos diferentes:
- **Fase 1**: Ejercicios, ejecución de código, submissions (datos operacionales del estudiante).
- **Fase 2**: Tutor IA, sesiones de chat, historial de conversaciones (datos cognitivos de interacción).
- **Fase 3**: Clasificación N4, CTR, cadena de hash, gobernanza, analytics de aula (datos cognitivos de evaluación, governance y analytics).

**El problema sin aislamiento:**

Sin separación explícita, en un monolito típico todos los modelos vivirían en el schema `public` de PostgreSQL. Esto crea:
- Ambigüedad sobre qué módulo "posee" qué tabla.
- Riesgo de un módulo modificando datos de otro (ya sea por bug o por decisión de diseño poco pensada).
- Dificultad para auditar qué operaciones realiza cada fase sobre qué datos.
- Conflictos en migraciones cuando dos subequipos tocan tablas del mismo schema simultáneamente.

**Restricciones del contexto:**

- Un único servidor PostgreSQL 16 (no se justifica sharding ni múltiples instancias para el scope de la tesis).
- Los subequipos necesitan poder hacer migraciones Alembic de forma independiente sin conflictos.
- Debe ser posible que un docente (Fase 4) consulte datos agregados de Fase 3 sin tener acceso a los datos raw de Fase 1.

---

### Decisión

**Definir cuatro schemas de PostgreSQL**, uno por fase, con ownership exclusivo:

```sql
CREATE SCHEMA IF NOT EXISTS operational;  -- Fases 0, 1 y 2: users, exercises, submissions, tutor_interactions, event_outbox
CREATE SCHEMA IF NOT EXISTS cognitive;    -- Fase 3 ÚNICAMENTE: cognitive_sessions, cognitive_events, cognitive_metrics
CREATE SCHEMA IF NOT EXISTS governance;   -- Fase 2 escribe governance_events, Admin gestiona tutor_system_prompts, Fase 3 audita
CREATE SCHEMA IF NOT EXISTS analytics;    -- Fase 3: aggregated_metrics, learning_analytics
```

> **Nota**: `tutor_interactions` pertenece al schema `operational` y es escrita por la Fase 2 (tutor). La Fase 3 (cognitive) la lee vía REST, nunca con queries directos.

**Reglas de ownership:**

| Schema | Owner (escribe) | Lectores (via REST) |
|--------|-----------------|---------------------|
| `operational` | Fases 0, 1 y 2 | Fase 3 (submissions y tutor_interactions para contexto CTR) |
| `cognitive` | Fase 3 ÚNICAMENTE | Fase 3 misma (analytics de progreso); docentes ven métricas agregadas vía API, nunca CTR raw |
| `governance` | Fase 2 (governance_events) + Admin (tutor_system_prompts) | Fase 3 (auditoría), Tutor (lee prompt activo via REST) |
| `analytics` | Fase 3 | Todos (datos agregados y anonimizados) |

**Alembic multi-schema:**

Cada fase tiene su propio directorio de migraciones Alembic:

```
alembic/
├── versions/      # Migraciones unificadas con prefijo de schema
```

Las migraciones están organizadas en un único directorio `versions/` con prefijos descriptivos (p. ej. `operational_`, `cognitive_`, `governance_`) para facilitar la revisión. Cada schema puede migrarse de forma independiente usando `--version-path` si el equipo lo decide en el futuro.

**Cross-schema views (solo lectura, para analytics):**

```sql
-- Vista de analytics que cruza datos operacionales y cognitivos
-- Propiedad de Fase 4, solo lectura
CREATE VIEW analytics.student_progress_summary AS
SELECT
    o.student_id,
    o.exercise_id,
    COUNT(o.id) AS submission_count,
    MAX(o.score) AS best_score,
    c.latest_n4_level,
    c.session_count
FROM operational.submissions o
LEFT JOIN cognitive.student_n4_summary c ON o.student_id = c.student_id
GROUP BY o.student_id, o.exercise_id, c.latest_n4_level, c.session_count;
```

Las vistas cross-schema están **documentadas y son read-only**. Cualquier escritura cross-schema es un error de diseño.

---

### Consecuencias

**Positivas:**

- **Propiedad clara**: `SELECT pg_class.relname, pg_namespace.nspname FROM pg_class JOIN pg_namespace...` muestra quién posee qué. No hay ambigüedad.
- **Migraciones independientes**: Fase 1 puede hacer `alembic upgrade head` en su schema sin afectar a Fase 3.
- **Permisos de DB diferenciados**: El usuario de base de datos de Fase 1 solo tiene permisos en `operational`. Si sus credenciales son comprometidas, el atacante no puede acceder a `cognitive` o `governance`.
- **Facilita auditorías**: Para verificar qué datos tiene el sistema del estudiante, se puede buscar en `cognitive.*` sin revisar todo el schema `public`.

**Negativas / Riesgos:**

- **Joins cross-schema son SQL válido**: PostgreSQL permite `SELECT * FROM operational.submissions JOIN cognitive.ctr_entries...` directamente en SQL. La barrera es solo convención/linter, no enforcement técnico estricto. (A diferencia de microservicios donde cruzar datos requiere una llamada de red).
- **Complejidad de Alembic multi-target**: Manejar múltiples directorios de migraciones Alembic requiere scripts custom para `alembic upgrade`. Se documenta en el README de contribución.
- **Foreign keys cross-schema son complicadas**: PostgreSQL las permite, pero hacen que las migraciones sean más difíciles de ordenar. Decisión: **no usar FK cross-schema**. Las referencias entre schemas usan UUID sin FK constraint, y la integridad se mantiene por lógica de aplicación.

**Neutrales:**

- Los schemas son una feature nativa de PostgreSQL sin overhead de performance. Un join entre `operational.submissions` y `cognitive.ctr_entries` es igual de eficiente que un join entre dos tablas en el mismo schema.

---

### Alternativas Consideradas

**Opción A: Schema único `public` con prefijos en nombres de tablas**
- `phase1_exercises`, `phase3_ctr_entries`, etc.
- *Rechazada*: Convención frágil sin enforcement. No hay forma de dar permisos de DB por fase. Cualquier código puede acceder a cualquier tabla sin restricción técnica.

**Opción B: Base de datos separada por fase**
- Cuatro bases de datos PostgreSQL separadas.
- *Rechazada*: Requiere cuatro servidores (o cuatro instancias), gestión de backups independiente, y hace imposibles los joins analíticos. El overhead operacional no está justificado para el scope de la tesis.

**Opción C: Schemas de PostgreSQL con Row Level Security (RLS)**
- Agregar RLS para control a nivel de fila.
- *Reservada como mejora futura*: RLS puede agregar aislamiento de datos por estudiante (un estudiante no puede ver datos de otro). Para la versión de tesis, el control a nivel de schema de aplicación es suficiente.

---

## ADRs Pendientes de Formalizar

Las siguientes decisiones están implementadas en el código pero aún no tienen ADR formal:

| # | Decisión | Impacto |
|---|----------|---------|
| ADR-008 (propuesto) | **Soft delete por defecto**: todas las entidades activas/inactivas usan `is_active: bool` o `deleted_at: datetime \| None`. Hard delete solo para registros efímeros. **Excepción**: eventos del CTR, code_snapshots, tutor_interactions y governance_events son inmutables. | Medio |
| ADR-009 (propuesto) | **Sin FK cross-schema**: Referencias entre schemas usan UUID sin constraint de FK. La integridad referencial se mantiene por lógica de aplicación. Esto permite migraciones independientes por schema sin dependencias de orden. | Medio |

---

## Registro de Cambios

| Fecha | ADR | Cambio | Autor |
|-------|-----|--------|-------|
| 2026-01-15 | ADR-001 | Versión inicial | Equipo |
| 2026-01-20 | ADR-002 | Versión inicial | Equipo |
| 2026-01-22 | ADR-003 | Versión inicial | Equipo |
| 2026-01-25 | ADR-004 | Versión inicial | Equipo |
| 2026-02-01 | ADR-005 | Versión inicial | Equipo |
| 2026-02-05 | ADR-006 | Versión inicial | Equipo |
| 2026-02-10 | ADR-007 | Versión inicial | Equipo |
| 2026-04-12 | ADR-007 | Fix schema ownership: cognitive → Fase 3 ÚNICAMENTE; operational → Fases 0,1,2; added tutor_interactions note | Equipo |

---

*Documento generado para el proyecto AI-Native — UTN FRM. Tesis doctoral sobre evaluación cognitiva asistida por IA en educación en programación.*
*Los ADRs deben actualizarse cuando las decisiones cambien. Un ADR nunca se elimina — se marca como Deprecado o Reemplazado.*
