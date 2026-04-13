# Resumen Consolidado — 02-arquitectura

> Generado archivo por archivo mientras se lee. 7 archivos en total.
> Última actualización: 2026-04-13

---

## 01_arquitectura_general.md — Datos Clave

### Stack y puertos
- Frontend: React 19 + Zustand 5 + TailwindCSS 4 + Vite → puerto 5173
- Backend: FastAPI 0.115 + Python 3.12 → puerto 8000
- DB: PostgreSQL 16 (4 schemas)
- Cache/EventBus: Redis 7 (Streams + Sets, at-least-once con consumer groups)
- LLM: Anthropic API (claude-sonnet-4-20250514)

### Modelo C4
- **Contexto**: 3 actores humanos (Estudiante, Docente, Admin) + 1 sistema externo (Anthropic)
- **Contenedores**: Frontend, Backend API, PostgreSQL, Redis, Anthropic API
- **Componentes documentados**: Feature Tutor (TutorRouter → TutorService → TutorRepo + LLMAdapter + GuardrailsPolicy), Feature Cognitive (CognitiveRouter → CognitiveService → CognitiveRepo + HashChainService)

### Nota sobre acceso docente a CTR
- **RESUELTO**: El docente puede ver la traza cognitiva procesada (timeline de eventos) vía REST endpoint GET /teacher/sessions/{id}/trace. No accede a cognitive_events por SQL directo.

### Arquitectura en capas (estricta)
```
Router (transporte) → Service (dominio) → Repository (datos) → Model (ORM)
```
- Router: deserialización, validación Pydantic, auth JWT, rate limiting, serialización. CERO lógica de negocio.
- Service: lógica de negocio, orquestación, validaciones dominio. NO conoce HTTP. Lanza DomainError, NO HTTPException.
- Repository: CRUD SQLAlchemy, queries, eager/lazy loading. NO lógica de negocio. Recibe AsyncSession por DI.
- Model: mapeo ORM, constraints, schemas, índices, relaciones.

### Reglas de capas
1. Capas solo conocen la inmediatamente inferior
2. Services no importan tipos FastAPI
3. Repositories reciben AsyncSession por constructor injection
4. DomainError → Router convierte a HTTPException

### Schemas PostgreSQL — Ownership
| Schema | Owner | Tablas | Readers |
|--------|-------|--------|---------|
| operational | Fases 0, 1, 2 | users, courses, commissions, exercises, submissions, code_snapshots, enrollments, tutor_interactions, event_outbox | cognitive (via REST) |
| cognitive | Fase 3 | cognitive_sessions, cognitive_events, reasoning_records, cognitive_metrics | analytics, governance (via REST) |
| governance | Fase 2 (escribe governance_events) + Admin (gestiona tutor_system_prompts) | tutor (via REST, lee prompt activo), Fase 3 (auditoría) |
| analytics | Fase 3 | risk_assessments | docentes via API |

**Nota importante**: Tabla `event_outbox` mencionada aquí NO aparecía en 01-negocio. Es nueva info.

### No cross-schema SQL joins (por diseño)
Razones: acoplamiento, ownership difuso, testing independiente, migración futura a microservicios.

### Estructura Backend
- `app/main.py` → FastAPI factory
- `app/config.py` → Pydantic BaseSettings
- `app/core/` → security (JWT, bcrypt), exceptions (DomainError), logging (structlog + request_id)
- `app/features/` → auth, courses, exercises, sandbox, tutor, cognitive, evaluation, governance
- `app/shared/` → db (session, base, UoW), models (por schema), repositories (base + concretos), schemas (responses)

### Estructura Frontend
- `src/features/` → auth, student, exercise, teacher
- Cada feature: components/, hooks/, store/, api/, types.ts
- `src/shared/` → components, hooks, api (axiosInstance), types, utils
- Router: React Router v7

### Patrones de comunicación entre fases
1. **Event Bus** (Redis Streams): Fases 1,2 emiten → Fase 3 consume. Streams: "events:submissions", "events:tutor"
2. **REST interno**: Cuando un dominio necesita datos de otro, usa API REST (no imports directos)
3. **WebSocket**: Tutor chat streaming. Frontend → WS /ws/tutor/chat?token=jwt → Backend → Anthropic API (streaming) → tokens via WS al frontend

### Decisión: Monolito Modular (no microservicios)
- La complejidad está en el dominio, no en la infra
- Volumen universitario < 500 usuarios concurrentes
- Schemas PostgreSQL = frontera real de ownership
- REST contracts + Redis events = camino de extracción a microservicios si fuera necesario
- **Revisar si**: >5000 usuarios, deploys se bloquean, stacks distintos, >8 personas en paralelo

### Convenciones de nomenclatura
| Elemento | Convención |
|----------|-----------|
| Archivos | snake_case |
| Clases | PascalCase |
| Variables/funciones | snake_case |
| Constantes | UPPER_SNAKE |
| Endpoints | kebab-case |
| Schema tables | snake_case |

### GuardrailsPolicy (componentes)
- AntiSolverGuard: bloquea respuestas directas
- ToneGuard: valida tono socrático
- LengthGuard: limita tokens de respuesta

---

## 02_modelo_de_datos.md — Datos Clave

### Principios del modelo
- **Inmutabilidad CTR**: cognitive_events y reasoning_records = solo INSERT, nunca UPDATE/DELETE. Sin is_active ni deleted_at. Permisos PostgreSQL lo enforcement.
- **UUID v4** como PK en todas las tablas (generación client-side, sin exposición de secuencias)
- **Timestamps UTC**: TIMESTAMPTZ en todas las tablas
- **Naming DB**: tablas=snake_case plural, columnas=snake_case, PKs=id, FKs={tabla_singular}_id, índices=ix_{tabla}_{col}, constraints=uq_{tabla}_{cols}

### Schema operational — Tablas detalladas

| Tabla | Campos clave adicionales (no vistos en 01-negocio) | Notas |
|-------|------------------------------------------------------|-------|
| users | password_hash (VARCHAR 128, bcrypt factor 12), role ENUM('alumno','docente','admin'), is_active | teacher_id FK en commissions (1:N user→comisiones) |
| courses | topic_taxonomy (JSONB, árbol de temas) | SIN semester como campo (difiere de 01-negocio) |
| commissions | teacher_id (FK → users.id), year (SMALLINT), semester (CHECK 1 or 2) | Relación explícita docente→comisión |
| exercises | **commission_id (FK → commissions.id)** ← INCONSISTENCIA CON FIX PREVIO | language, starter_code, max_attempts, time_limit_minutes, order_index, topic_tags (TEXT[]) |
| submissions | attempt_number, feedback, evaluated_at | score=NUMERIC(5,2) 0-100 |
| code_snapshots | Sin edit_distance_from_previous (mencionado en 01-negocio pero no en modelo) | Inmutable, sin soft delete |
| reflections | **TABLA NUEVA** no mencionada en 01-negocio | difficulty_perception(1-5), strategy_description, ai_usage_evaluation, what_would_change, confidence_level(1-5). FK a submission (1:1) |
| tutor_interactions | student_id, exercise_id como FKs directas. Sin session_id (difiere de 01-negocio) | n4_level=SMALLINT CHECK(1-4), append-only |
| event_outbox | event_type, payload(JSONB), status(pending/processed/failed), retry_count | Outbox pattern para at-least-once |

### INCONSISTENCIA CRÍTICA IC-A2: exercises.commission_id persiste aquí

**En el fix de 01-negocio cambiamos exercises a course_id, pero aquí el modelo de datos detallado dice commission_id**. Este archivo es la referencia autoritativa del modelo de datos. Necesita alinearse.

### INCONSISTENCIA IC-A3: courses sin campo semester

- 01-negocio/03_features_y_epics.md dice: `courses: id, name, description, semester, is_active`
- 02-arquitectura/02_modelo_de_datos.md NO tiene `semester` en courses (solo en commissions)
- **Resolución**: semester en commissions tiene más sentido (un curso como "Algoritmos" existe siempre, las comisiones son por año/semestre)

### INCONSISTENCIA IC-A4: tutor_interactions sin session_id

- 01-negocio/03_features_y_epics.md dice session_id (correlación lógica con cognitive_sessions)
- 02-arquitectura/02_modelo_de_datos.md tiene student_id + exercise_id, sin session_id
- La vinculación se haría por (student_id, exercise_id, rango temporal) en vez de session_id directo

### INCONSISTENCIA IC-A5: code_snapshots sin edit_distance

- 01-negocio/04_reglas_de_negocio.md (RO-6) menciona `edit_distance_from_previous`
- 02-arquitectura/02_modelo_de_datos.md no incluye este campo
- **Decisión necesaria**: ¿Se agrega o se calcula on-the-fly?

### INCONSISTENCIA IC-A6: cognitive_events — catálogo event_type diverge

El catálogo en 02_modelo_de_datos.md difiere del mapeo en 01-negocio/03:

| En 01-negocio | En 02-arquitectura | Nota |
|---------------|-------------------|------|
| reads_problem | reads_problem | OK |
| asks_clarification | — | FALTA en 02 |
| reformulates_problem | — | FALTA en 02 |
| defines_strategy | — | FALTA en 02 |
| changes_strategy | — | FALTA en 02 |
| asks_hint | — | FALTA en 02 |
| runs_test | code.run | NOMBRE DISTINTO |
| interprets_error | — | FALTA en 02 |
| fixes_error | — | FALTA en 02 |
| asks_explanation | tutor.question_asked | NOMBRE DISTINTO |
| audits_ai_suggestion | — | FALTA en 02 |
| submits_reflection | reflection.submitted | NOMBRE DISTINTO |
| — | session.started | NUEVO en 02 |
| — | code.snapshot | NUEVO en 02 |
| — | tutor.response_received | NUEVO en 02 |
| — | submission.created | NUEVO en 02 |
| — | session.closed | NUEVO en 02 |

**Impacto ALTO**: El mapeo event_type → N4 es fundamental para el motor cognitivo. Los dos documentos usan catálogos completamente distintos.

### INCONSISTENCIA IC-A7: cognitive_metrics incompleto (otra vez)

02_modelo_de_datos.md NO tiene: qe_score, qe_components, dependency_score, reflection_score, success_efficiency.
Coincide con la versión original de 01-negocio (pre-fix). El fix de 01-negocio agregó estos campos pero este doc no los tiene.

### INCONSISTENCIA IC-A8: cognitive_events hash formula

- 01-negocio dice: `hash(n) = SHA256(hash(n-1) + datos(n))`
- 02-arquitectura dice: `hash(n) = SHA256(hash(n-1) + event_type + serialize(payload) + created_at.isoformat())`
- La de 02 es más específica y correcta (la implementación). La de 01 es abreviada.
- No es error real, pero deben estar alineadas.

### INCONSISTENCIA IC-A9: cognitive_events campo event_hash vs current_hash

- El schema dice campo = `event_hash`
- La implementación Python (verify_chain) referencia `current_hash`
- **Deben usar el mismo nombre**

### INCONSISTENCIA IC-A10: risk_assessments tiene commission_id, no course_id

- 01-negocio dice: `risk_assessments: student_id, course_id`
- 02-arquitectura dice: `risk_assessments: student_id, commission_id`
- **commission_id tiene más sentido** (el riesgo se evalúa en contexto de una comisión específica)

### Tabla reflections (NUEVA)
- No mencionada en 01-negocio como tabla separada
- En 01-negocio, la reflexión se mencionaba como parte de Fase 2 pero no como tabla propia con schema detallado
- Campos: difficulty_perception (1-5), strategy_description, ai_usage_evaluation, what_would_change, confidence_level (1-5)
- FK UNIQUE a submissions (1:1)
- Owner: Fase 2 (operational schema)

### Hash Chain — Implementación
- Génesis: `SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())`
- Evento: `SHA256(previous_hash + event_type + serialize(payload) + created_at.isoformat())`
- serialize = json.dumps(sort_keys=True, separators=(",",":")) — determinista
- Verificación: pública y determinista, no requiere clave privada
- Se rechazó JWT/signed tokens porque el server podría re-firmar eventos alterados

### Soft Delete
- CON soft delete (is_active): users, courses, commissions, exercises, enrollments
- SIN soft delete (inmutables): code_snapshots, tutor_interactions, cognitive_events, reasoning_records, governance_events
- BaseRepository implementa get_active() y soft_delete()

### Estrategia de índices
- Indexar TODAS las FKs
- Índices compuestos para queries multi-filtro frecuentes
- GIN para arrays (topic_tags) y JSONB
- Índices parciales (WHERE is_active=TRUE)
- Índice parcial UNIQUE para prompt activo (solo 1 activo a la vez)

---

## 03_api_y_endpoints.md — Datos Clave

### Convenciones
- Base URL: `/api/v1/`
- Wrapper estándar: `{ status, data, meta, errors }` en TODA respuesta
- Paginación: `page`, `per_page` (max 100), `sort_by`, `sort_dir`
- Error format: `{ code, message, field }`

### Auth
- Access token JWT 15min, refresh token 7d en cookie HttpOnly (SameSite=Strict)
- JWT payload: sub, email, role, iat, exp, jti
- WS auth via query param `?token=<jwt>`, código 4001 si inválido
- Registro NO envía tokens (requiere login explícito)

### Endpoints documentados

**Fase 0 — Auth (4 endpoints)**:
- POST /auth/register (5 req/min por IP)
- POST /auth/login (10 req/5min por IP)
- POST /auth/refresh (30 req/min por usuario)
- POST /auth/logout

**Fase 1 — Core (13 endpoints)**:
- CRUD courses (GET list, POST, GET detail, PUT, DELETE)
- Commissions: GET /courses/{id}/commissions, POST, GET /commissions/{id}, PUT
- Enrollments: POST /commissions/{id}/enrollments (alumno self-enroll), GET teacher/commissions/{id}/enrollments, DELETE
- Exercises: GET /courses/{course_id}/exercises, POST, GET /exercises/{id}, PUT, DELETE
- Sandbox: POST /student/exercises/{id}/run (30 req/min)
- Submissions: POST /student/exercises/{id}/submit (10 req/min), GET student/exercises/{id}/submissions, GET student/submissions/{id}
- Snapshots: POST /exercises/{id}/snapshots (1 req/30s)

**Fase 2 — Tutor (8 endpoints)**:
- WS /ws/tutor/chat (init, message, token streaming, complete, error, rate_limit)
- POST /submissions/{id}/reflection (5 req/hora)
- GET /submissions/{id}/reflection
- GET /teacher/tutor/interactions (filtrable por student, exercise, commission, date, n4_level)
- CRUD admin/tutor/system-prompts (GET list, POST, PUT, DELETE)
- POST admin/tutor/system-prompts/{id}/activate

**Fase 3 — Cognitive (4 endpoints, solo GET)**:
- GET /teacher/courses/{id}/dashboard (10 req/min)
- GET /teacher/students/{id}/profile
- GET /teacher/sessions/{id}/trace (?verify_integrity=true)
- GET /teacher/exercises/{id}/patterns (5 req/min)

### Lifecycle de cognitive sessions (IMPORTANTE)
- Sessions y events se crean INTERNAMENTE por Event Bus consumer de Fase 3
- NO hay endpoints de mutación expuestos al frontend
- Session se crea al llegar primer evento (reads_problem)
- Session se cierra al llegar exercise.submitted o por inactividad (30min)

### INCONSISTENCIA IC-A11: Exercises bajo commissions en API

- Los endpoints usan `/courses/{course_id}/exercises` — exercises pertenecen a courses (corregido)
- En fix de 01-negocio decidimos exercises → courses (course_id FK)
- Si exercises son de courses, la API debería ser `/courses/{course_id}/exercises`
- **Impacto**: Hay que alinear API con decisión de modelo de datos

### INCONSISTENCIA IC-A12: Reflexión — campos divergen entre API y modelo

- API reflection request: `responses: { what_worked, what_was_difficult, what_would_you_do_differently }`
- Modelo reflections tabla: difficulty_perception, strategy_description, ai_usage_evaluation, what_would_change, confidence_level
- **Los campos son completamente diferentes**. Ni los nombres ni la estructura coinciden.

### INCONSISTENCIA IC-A13: cognitive session creation

- API doc dice: "Session se crea al llegar el primer evento (reads_problem)"
- 01-negocio/05_flujos_principales.md paso 4: "Se inicia sesión cognitiva → POST /cognitive/sessions/start Fase 3"
- **Contradicción**: ¿La sesión se crea explícitamente vía endpoint o implícitamente vía Event Bus?

### WS Protocol
- Tipos cliente→server: `init` (exercise_id + current_code), `message` (content)
- Tipos server→cliente: `token` (streaming), `complete` (interaction_id, tokens_used), `error`, `rate_limit`
- Códigos cierre: 1000 normal, 4001 auth, 4002 sesión expirada, 4003 rate limit, 4004 formato inválido, 4005 error interno

### Rate Limiting
- Algoritmo: Sliding Window con Redis (ZSET)
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After
- 27 error codes documentados

### Nota sobre tutor messages rate limit
- 01-negocio dice 30 msg/hora por alumno por ejercicio
- API doc dice lo mismo: 30 msg/hora por alumno por ejercicio para WS chat
- Consistente

---

## 04_patrones_de_diseno.md — Datos Clave

### 8 patrones documentados con implementación completa

| Patrón | Ubicación | Beneficio |
|--------|-----------|-----------|
| Repository | shared/repositories/ | Queries encapsuladas, testabilidad |
| Unit of Work | shared/db/unit_of_work.py | Transaccionalidad, sin commits accidentales |
| Domain Service | features/*/service.py | Lógica pura, sin HTTP |
| Event Bus | core/event_bus.py | Desacoplamiento inter-dominio via Redis Streams |
| Hash Chain | features/cognitive/hash_chain.py | Integridad CTR |
| Dependency Injection | dependencies.py + Depends() | Composición, testabilidad |
| Strategy (LLM) | features/tutor/adapters.py | Vendor independence, fallback |
| Guard/Policy | features/tutor/guardrails.py | Guardrails componibles y auditables |

### Repository Pattern
- BaseRepository con CRUD genérico (get_by_id, get_active_by_id, list_all con paginación, save, soft_delete)
- Repos específicos extienden con queries de dominio (ej: get_latest_by_student_exercise)
- Anti-patrón: Service haciendo queries SQL directamente

### Unit of Work
- UoW como context manager async (async with)
- Inicializa todos los repos con la misma sesión
- Commit explícito, rollback automático en excepción
- Repos NUNCA commitean, solo flushean

### Domain Service
- DomainError base con code + message
- Subclases: NotFoundException, NotEnrolledException, SessionAlreadyOpenException
- Router captura DomainError → convierte a HTTPException
- Anti-patrón: HTTPException en service, lógica de negocio en router

### Event Bus (Redis Streams)
- 3 streams: events:submissions, events:tutor, events:cognitive
- Consumer groups para at-least-once delivery
- ACK solo si handler exitoso, reintento automático si falla
- Consumers corren en background via asyncio.create_task en lifespan
- DomainEvent base con event_type, correlation_id, timestamp
- Anti-patrón: llamadas directas entre services de dominios distintos

### NOTA: CognitiveService tiene start_session()
- El CognitiveService tiene método `start_session()` explícito
- Confirma que la cognitive session se puede crear explícitamente (no solo vía Event Bus)
- Contradice parcialmente API doc que dice "sessions se crean internamente"
- **Resolución probable**: Ambos mecanismos existen — explícito vía endpoint Y automático vía Event Bus como fallback

### Strategy Pattern — LLM Adapters
- LLMAdapter Protocol con: stream() → AsyncIterator[LLMStreamChunk], complete() → str
- Implementaciones: AnthropicAdapter (default, claude-sonnet-4-20250514), FakeLLMAdapter (tests)
- OpenAIAdapter y OllamaAdapter mencionados pero no implementados (P3)
- Factory create_llm_adapter(config) retorna el adapter configurado
- LLMStreamChunk: text, is_final, tokens_used, model_version

### Guard/Policy Pattern
- GuardrailsPolicy con guards componibles
- Cada guard puede bloquear/reformular respuesta del LLM
- Si violación → governance_event registrado

---

## 05_eventos_y_websocket.md — Datos Clave

### Dos dimensiones de tiempo real
1. **WebSocket streaming**: tutor IA → tokens → frontend (< 100ms primer token)
2. **Redis Streams Event Bus**: Fases 1,2 → eventos → Fase 3 (at-least-once + outbox)

### Event Bus — 3 streams (no 2 como decía 04_patrones)
- `events:submissions` (EventBus.STREAM_SUBMISSIONS)
- `events:tutor` (EventBus.STREAM_TUTOR)
- `events:code` (EventBus.STREAM_CODE) ← **NUEVO**, no mencionado en otros docs

### Outbox Pattern
- Tabla `event_outbox` en PostgreSQL como fallback transaccional
- Estrategia dual: Redis Streams (primario) + Outbox polling cada 5s (fallback)
- Outbox para garantizar at-least-once cuando Redis no disponible
- Campos: id, event_type, payload(JSONB), status(pending/processed/failed), retry_count, processed_at

### EventType canónico (bus de eventos, DIFERENTE de event_types del CTR)

**Bus events (lo que viaja por Redis/Outbox):**
- Fase 1: reads_problem, code.snapshot.captured, code.executed, code.execution.failed, exercise.submitted, reflection.submitted
- Fase 2: tutor.session.started, tutor.interaction.completed, tutor.session.ended
- Fase 3: cognitive.classified, session.metrics.computed, ctr.entry.created, ctr.hash.verified
- Governance: governance.flag.raised, governance.prompt_updated

**CTR event_types (lo que se persiste en cognitive_events — DISTINTOS del bus):**
- session.started, reads_problem, code.snapshot, tutor.question_asked, tutor.response_received, code.run, submission.created, reflection.submitted, session.closed

**NOTA CLAVE**: "Son los event_type canónicos que el Cognitive Trace Engine persiste en DB. Distintos de los nombres del bus Redis — la Fase 3 los transforma al consumir."

### INCONSISTENCIA IC-A14: TRES catálogos de event_type diferentes

Ahora tenemos 3 catálogos incompatibles:
1. **01-negocio/03** (mapeo N4): reads_problem, asks_clarification, reformulates_problem, defines_strategy, changes_strategy, asks_hint, runs_test, interprets_error, fixes_error, asks_explanation, audits_ai_suggestion, submits_reflection
2. **02-arquitectura/02** (modelo datos): session.started, reads_problem, code.snapshot, tutor.question_asked, tutor.response_received, code.run, submission.created, reflection.submitted, session.closed
3. **02-arquitectura/05** (bus): reads_problem, code.snapshot.captured, code.executed, exercise.submitted, tutor.interaction.completed, etc.

La doc de 05 dice explícitamente que los nombres del bus y del CTR son DIFERENTES (Fase 3 transforma al consumir). Pero 01-negocio tiene un tercer set de nombres que no coincide con ninguno de los dos.

### Mapeo N4 (de 05_eventos, difiere de 01-negocio)

| CTR event_type | N4 Level |
|---------------|---------|
| reads_problem | N1 |
| reflection.submitted | N1 |
| code.snapshot | N2 |
| submission.created | N2 |
| code.run | N3 |
| tutor.question_asked | N4 |
| tutor.response_received | N4 |

vs 01-negocio: reads_problem=N1, asks_clarification=N1, defines_strategy=N2, runs_test=N3, asks_explanation=N4...

**DIFERENCIAS IMPORTANTES**:
- code.snapshot → N2 en 05, no existe en 01
- submission.created → N2 en 05, no existe en 01
- reflection.submitted → N1 en 05, sin N4 en 01 (lo marcamos como metacognitivo)
- 01 tiene muchos event_types granulares (asks_hint, interprets_error, etc.) que 05 NO tiene

### Indicadores comportamentales (NUEVO, solo en 05)
- CognitiveBehaviorIndicator: inferidos del análisis de patrones, NO almacenados como events
- Ejemplos: asked_basic_concept, no_progress_10min, fixed_logic_error_independently
- Mapeados a N4 levels

### Clasificación N4 de sesión
- Ventana de 15 minutos de eventos recientes
- Ponderación: N1=1, N2=2, N3=3, N4=4
- Resultado = nivel con mayor peso ponderado

### Code Snapshots
- Periódico cada 30s (solo si cambió)
- En ejecución (incluido en evento code.executed)
- Trigger: "periodic" | "execution" | "submission"
- Backend publica `code.snapshot.captured` en stream `events:code`

### Escalabilidad
- v1: 30-50 estudiantes concurrentes (un proceso uvicorn async)
- Mediano plazo: Nginx + workers, Redis Cluster, debounce snapshots a 1/min

### WS Reconexión
- Backoff exponencial documentado
- Heartbeat ping/pong
- Reset retry count on successful reconnect

---

## 06_abstracciones_y_contratos.md — Datos Clave

### Filosofía de contratos
- Cada módulo expone interfaz pública, oculta implementación
- Schema de datos lo define el módulo propietario
- Contratos versionados — cambios breaking requieren /v2/ + deprecación de 1 sprint
- Abstracciones retrasan acoplamiento, no lo eliminan

### Regla de dependencias (unidireccional)
```
auth, courses, exercises, sandbox, tutor → shared (operational)
cognitive, evaluation → shared (cognitive, consume via event bus)
governance → shared (governance)
NUNCA: exercises importa de cognitive, etc.
```

### OpenAPI como fuente de verdad
- FastAPI genera OpenAPI 3.1 en /openapi.json
- Tipos TypeScript auto-generados: `npx openapi-typescript`
- Tags: auth, courses, exercises, tutor, cognitive, governance

### Enforcement de ownership
- BaseRepository con OWNED_SCHEMA obligatorio
- Linter pre-commit verifica que no se acceda a tablas de otro schema

### Cross-module communication
- Phase 3 → Phase 1 via REST HTTP con httpx.AsyncClient interno
- Header `X-Internal-Service: phase3` para identificar llamadas internas

### Jerarquía de excepciones
- DomainError (base) con code, message, details
- Subclases: NotFoundError, AuthorizationError, ValidationError, MaxAttemptsReachedError, CTRIntegrityError, SecurityViolationError, RateLimitExceededError
- HTTP_STATUS_MAP mapea codes a HTTP status
- Exception handler global registrado en main.py

### INCONSISTENCIA IC-A15: Nombre de clase DomainError vs DomainError
- 04_patrones_de_diseno.md usa `DomainError`
- 06_abstracciones_y_contratos.md usa `DomainError`
- **Deben unificarse a un solo nombre**

### Invariantes como código
- Submission: código no vacío, max_attempts check
- CognitiveSession: can_submit check
- Implementados en __post_init__ de dataclasses de dominio

---

## 07_adrs.md — Datos Clave

### 7 ADRs documentadas, todas estado "Aceptado"

| ADR | Decisión | Alternativas descartadas |
|-----|----------|-------------------------|
| ADR-001 | Monolito Modular | Microservicios |
| ADR-002 | Hash Chain SHA-256 para CTR | JWT signed tokens, blockchain distribuido |
| ADR-003 | WebSocket Streaming para tutor | SSE, Long Polling |
| ADR-004 | Event Bus Redis Streams + Outbox | Kafka, RabbitMQ, solo outbox, llamada síncrona |
| ADR-005 | Sandbox subprocess + setrlimit | Docker por ejecución, gVisor, WebAssembly/Pyodide |
| ADR-006 | LLM Protocol Adapters | Acoplamiento directo a Anthropic |
| ADR-007 | 4 Schemas PostgreSQL | Schema único, DB por servicio |

### ADR-004 detalle (Event Bus)
- 4 streams: events:submissions, events:tutor, events:code, events:cognitive
- Dual: Redis Streams (primario, <5ms) + Outbox polling 5s (fallback)
- Consistencia eventual aceptable (<100ms vía Redis, <5s vía outbox)
- Orden de eventos entre streams: determinado por timestamp, no por llegada

### ADR-005 detalle (Sandbox)
- 3 capas: timeout 10s, memory 128MB (setrlimit), seccomp Docker (prod)
- Solo Python en v1
- setrlimit solo en Linux (OK para UTN)
- Bypass potencial vía ctypes — blacklist de imports como mitigación futura

### ADR-007 nota
- 4 schemas confirmados: operational, cognitive, governance, analytics
- Ownership explícito: GRANT SELECT a otros, no INSERT/UPDATE/DELETE

---

## INCONSISTENCIAS DETECTADAS

### IC-A1: Acceso docente a CTR crudo vs métricas agregadas

- **02-arquitectura/01**: "No tiene acceso a las trazas CTR crudas (`cognitive_events`) — solo a dashboards y métricas agregadas"
- **01-negocio/02_actores_y_roles.md**: RBAC dice docente puede "ver (su comisión)" la Traza cognitiva (CTR)
- **01-negocio/05_flujos_principales.md**: Flujo 3 muestra al docente viendo "timeline visual con eventos color-coded", que implica acceso a eventos individuales
- **Pendiente resolución**: ¿Ve eventos crudos filtrados o una vista procesada/agregada?

### IC-A2: exercises.commission_id persiste en 02_modelo_de_datos.md (CRÍTICA)
- Ya corregimos a course_id en 01-negocio, pero el modelo de datos detallado en 02 sigue con commission_id
- El ER diagram, la tabla exercises, los índices, y los endpoints de API usan commission_id
- **Necesita fix en**: 02_modelo_de_datos.md (tabla, ER, índices), 03_api_y_endpoints.md (rutas bajo /commissions/)

### IC-A3: courses sin campo semester
- 01-negocio dice courses tiene semester, 02-arquitectura no lo tiene
- semester vive en commissions (year + semester), que tiene más sentido
- **Fix**: Eliminar semester de courses en 01-negocio/03_features_y_epics.md

### IC-A4: tutor_interactions sin session_id en modelo detallado
- 01-negocio dice session_id (correlación lógica), 02-arquitectura tiene student_id+exercise_id sin session_id
- **Decisión**: Agregar session_id como campo correlacional también en 02

### IC-A5: code_snapshots sin edit_distance
- Mencionado en 01-negocio pero no en modelo detallado
- **Decisión**: Se calcula on-the-fly, no se almacena. Remover de 01-negocio.

### IC-A6: Catálogo event_type completamente divergente entre 01-negocio y 02-arquitectura (CRÍTICA)
- 01-negocio tiene nombres semánticos del dominio: asks_clarification, defines_strategy, etc.
- 02-arquitectura tiene nombres técnicos del CTR: code.run, tutor.question_asked, etc.
- **Decisión necesaria**: Elegir UN catálogo canónico. Ver también IC-A14.

### IC-A7: cognitive_metrics incompleto en 02_modelo_de_datos.md
- Falta: qe_score, qe_components, dependency_score, reflection_score, success_efficiency

### IC-A8: Hash formula — abreviada vs detallada (menor)
- 01-negocio abreviada, 02-arquitectura detallada. No es error real.

### IC-A9: cognitive_events campo event_hash vs current_hash
- Schema dice event_hash, implementación Python dice current_hash
- **Fix**: Unificar a event_hash (es el nombre en la tabla)

### IC-A10: risk_assessments — commission_id vs course_id
- 01-negocio dice course_id, 02-arquitectura dice commission_id
- **Decisión**: commission_id (más granular, correcto)

### IC-A11: Exercises bajo /commissions/ en API
- Si exercises → courses, la API debería ser /courses/{id}/exercises
- **Necesita fix en API**

### IC-A12: Reflexión — campos API vs modelo (CRÍTICA)
- API: what_worked, what_was_difficult, what_would_you_do_differently
- Modelo: difficulty_perception, strategy_description, ai_usage_evaluation, what_would_change, confidence_level
- **Son completamente distintos. Necesita unificación.**

### IC-A13: Cognitive session creation — explícita vs Event Bus
- API dice Event Bus (automática), 04_patrones tiene start_session() (explícita)
- **Decisión**: Ambos mecanismos coexisten. Endpoint explícito como primario, Event Bus como fallback.

### IC-A14: TRES catálogos de event_type incompatibles (CRÍTICA)
- 01-negocio: semánticos (asks_clarification, defines_strategy...)
- 02/02_modelo: CTR (code.run, tutor.question_asked...)
- 02/05_eventos: bus (code.executed, tutor.interaction.completed...)
- Doc de 05 explica: bus y CTR son DIFERENTES, Fase 3 transforma al consumir
- Pero 01-negocio tiene un tercer set que no coincide con ninguno
- **Necesita un mapeo unificado de 3 niveles**: bus event → CTR event → N4 level

### IC-A15: DomainError vs DomainError
- 04_patrones usa DomainError, 06_abstracciones usa DomainError
- **Fix**: Unificar a DomainError (más pythónico)

---

## FIXES APLICADOS

1. **exercises FK** → course_id en 02_modelo_de_datos.md y 03_api_y_endpoints.md ✅
2. **Event types** → Mapeo unificado 3 niveles (bus → CTR → N4) en 01-negocio/03 ✅
3. **Reflexión campos** → API alineada con modelo de tabla en 03_api_y_endpoints.md ✅
4. **Cognitive session** → Documentado mecanismo dual en 03_api_y_endpoints.md ✅
5. **DomainError** → Nombre unificado en 04_patrones_de_diseno.md ✅
6. **cognitive_metrics** → Campos Qe + dependency + reflection + efficiency en 02_modelo_de_datos.md ✅
7. **event_hash** → Nombre unificado en 02_modelo_de_datos.md ✅
8. **risk_assessments** → commission_id restaurado en 02_modelo_de_datos.md, corregido en 01-negocio ✅
9. **courses.semester** → Removido de 01-negocio/03 ✅
10. **edit_distance** → Nota "on-the-fly" en 01-negocio/04 ✅
11. **tutor_interactions.session_id** → Agregado en 02_modelo_de_datos.md ✅
