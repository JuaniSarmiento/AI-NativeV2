# Arquitectura General — Plataforma AI-Native

**Versión**: 1.0  
**Fecha**: 2026-04-10  
**Estado**: Referencia autoritativa  

---

## Tabla de Contenidos

1. [Visión General](#1-vision-general)
2. [Modelo C4 — Nivel Contexto](#2-modelo-c4--nivel-contexto)
3. [Modelo C4 — Nivel Contenedor](#3-modelo-c4--nivel-contenedor)
4. [Modelo C4 — Nivel Componente](#4-modelo-c4--nivel-componente)
5. [Arquitectura en Capas](#5-arquitectura-en-capas)
6. [Schemas PostgreSQL y Reglas de Ownership](#6-schemas-postgresql-y-reglas-de-ownership)
7. [Estructura del Backend](#7-estructura-del-backend)
8. [Estructura del Frontend](#8-estructura-del-frontend)
9. [Patrones de Comunicación entre Fases](#9-patrones-de-comunicación-entre-fases)
10. [Decisión Arquitectural: Monolito Modular vs. Microservicios](#10-decisión-arquitectural-monolito-modular-vs-microservicios)

---

## 1. Visión General

La Plataforma AI-Native es un sistema universitario para la enseñanza de programación que integra:

- **Tutor Socrático con IA**: Guía al estudiante mediante preguntas en lugar de dar soluciones directas.
- **Registro de Traza Cognitiva (CTR)**: Cadena de hash SHA-256 que garantiza la integridad inmutable del historial cognitivo del estudiante.
- **Modelo de Evaluación N4**: Niveles N1 (Comprensión), N2 (Estrategia), N3 (Validación), N4 (Interacción con IA).
- **Framework de Gobernanza**: Control de prompts del sistema, auditoría de interacciones y guardarraíles anti-solver.

La arquitectura está organizada en **4 fases de desarrollo** que mapean 1:1 a dominios de negocio y schemas de base de datos:

| Fase | Dominio | Schema PostgreSQL |
|------|---------|-------------------|
| 0 | Autenticación y usuarios | `operational` |
| 1 | Cursos, ejercicios, entregas | `operational` |
| 2 | Tutor socrático con IA | `operational` (tutor_interactions) |
| 3 | Traza cognitiva y evaluación | `cognitive`, `governance`, `analytics` |

---

## 2. Modelo C4 — Nivel Contexto

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PLATAFORMA AI-NATIVE                         │
│                                                                     │
│  ┌──────────────┐    interactúa vía     ┌─────────────────────────┐ │
│  │  ESTUDIANTE  │ ─────────────────────>│  Frontend Web (React)   │ │
│  │  (Alumno)    │                       │  puerto 5173            │ │
│  └──────────────┘                       └──────────┬──────────────┘ │
│                                                    │ REST/WebSocket │
│  ┌──────────────┐    monitorea vía      ┌──────────▼──────────────┐ │
│  │   DOCENTE    │ ─────────────────────>│  Backend API (FastAPI)  │ │
│  │  (Profesor)  │                       │  puerto 8000            │ │
│  └──────────────┘                       └──────────┬──────────────┘ │
│                                                    │                │
│  ┌──────────────┐    administra vía               │                │
│  │ ADMINISTRADOR│ ─────────────────────────────────┘                │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
         │                          │                    │
         ▼                          ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│  PostgreSQL 16   │  │    Redis 7       │  │   Anthropic API      │
│  (4 schemas)     │  │  (cache/streams) │  │ (Claude Sonnet/Haiku)│
└──────────────────┘  └──────────────────┘  └──────────────────────┘
```

### Actores del Sistema

**Estudiante**: Usuario principal. Resuelve ejercicios, interactúa con el tutor socrático, genera trazas cognitivas. Solo puede ver su propio CTR.

**Docente**: Monitorea el progreso de los estudiantes de sus comisiones. Puede ver entregas (`submissions`) e interacciones con el tutor (`tutor_interactions`) de los estudiantes de sus comisiones para diagnóstico pedagógico. No tiene acceso a las trazas CTR crudas (`cognitive_events`) — solo a dashboards y métricas agregadas derivadas del modelo N4.

**Administrador**: Gestiona la plataforma. Configura prompts del tutor, gestiona cursos y comisiones, audita la gobernanza del sistema.

**Sistema de IA (Anthropic Claude)**: Actor externo. Recibe contexto de ejercicio + historial socrático + guardarraíles. Devuelve respuestas en streaming vía WebSocket.

---

## 3. Modelo C4 — Nivel Contenedor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PLATAFORMA AI-NATIVE                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND (React 19 + Vite)                       │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ Auth Module  │  │ Course/Exer  │  │   Tutor Chat (WS)        │  │   │
│  │  │ Zustand Auth │  │ cise Module  │  │   Streaming UI           │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  │                                                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │                  Cognitive Dashboard                          │  │   │
│  │  │         (Solo docentes — visualización CTR)                  │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                     │ HTTPS / WSS                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BACKEND (FastAPI + Python 3.12)                  │   │
│  │                                                                     │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐  │   │
│  │  │ Auth       │  │ Core       │  │ Tutor      │  │ Cognitive   │  │   │
│  │  │ Feature    │  │ Feature    │  │ Feature    │  │ Feature     │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────────┘  │   │
│  │                                                                     │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────────┐   │   │
│  │  │ Evaluation │  │ Governance │  │ Sandbox (code execution)   │   │   │
│  │  │ Feature    │  │ Feature    │  └────────────────────────────┘   │   │
│  │  └────────────┘  └────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                    │                    │                      │
│  ┌─────────▼──────┐   ┌─────────▼──────┐   ┌────────▼────────┐           │
│  │  PostgreSQL 16 │   │    Redis 7      │   │  Anthropic API  │           │
│  │  schemas:      │   │  - Session TTL  │   │  - Streaming    │           │
│  │  operational   │   │  - Rate limit   │   │  - Guardrails   │           │
│  │  cognitive     │   │  - Event Bus    │   └─────────────────┘           │
│  │  governance    │   │  - Chat cache   │                                 │
│  │  analytics     │   └────────────────┘                                 │
│  └────────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Responsabilidades de Contenedores

| Contenedor | Tecnología | Responsabilidad Principal |
|------------|-----------|--------------------------|
| Frontend | React 19 + Zustand 5 + TailwindCSS 4 | UI/UX, estado local, streaming de chat |
| Backend API | FastAPI 0.115 + Python 3.12 | Lógica de negocio, orquestación, REST + WS |
| PostgreSQL 16 | 4 schemas separados | Persistencia transaccional, CTR |
| Redis 7 | Streams + Sets | Cache, rate limiting, Event Bus interno (at-least-once con consumer groups) |
| Anthropic API | claude-sonnet-4-20250514 | Generación de respuestas socráticas |

---

## 4. Modelo C4 — Nivel Componente

### Componentes del Backend (Feature: Tutor)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Feature: Tutor                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  TutorRouter (/ws/tutor/chat, /student/exercises/{id}/   │  │
│  │               reflection)                                │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │ Depends(get_tutor_service)          │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │  TutorService                                            │  │
│  │  - stream_chat()                                         │  │
│  │  - save_interaction()                                    │  │
│  │  - apply_guardrails()                                    │  │
│  │  - build_socratic_context()                              │  │
│  └───────┬───────────────────────────┬───────────────────────┘  │
│          │                           │                          │
│  ┌───────▼──────────┐    ┌───────────▼──────────────────────┐  │
│  │ TutorRepository  │    │ LLMAdapter (Protocol)             │  │
│  │ - save()         │    │ - AnthropicAdapter (default)      │  │
│  │ - get_history()  │    │ - OpenAIAdapter (fallback)        │  │
│  └──────────────────┘    │ - OllamaAdapter (local dev)       │  │
│                          └──────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  GuardrailsPolicy                                        │  │
│  │  - AntiSolverGuard: bloquea respuestas directas          │  │
│  │  - ToneGuard: valida tono socrático                      │  │
│  │  - LengthGuard: limita tokens de respuesta               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes del Backend (Feature: Cognitive)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feature: Cognitive                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CognitiveRouter                                         │  │
│  │  (/cognitive/sessions/*, /teacher/courses/{id}/*)        │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │  CognitiveService                                        │  │
│  │  - start_session()        - close_session()              │  │
│  │  - record_event()         - get_student_profile()        │  │
│  │  - calculate_n4_score()   - detect_patterns()            │  │
│  └────────┬──────────────────────┬────────────────────────────┘  │
│           │                      │                             │
│  ┌────────▼──────────┐  ┌────────▼───────────────────────┐   │
│  │ CognitiveRepo     │  │ HashChainService                │   │
│  │ - save_session()  │  │ - compute_hash()                │   │
│  │ - save_event()    │  │ - verify_chain_integrity()      │   │
│  │ - get_trace()     │  │ - get_last_hash()               │   │
│  └───────────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Arquitectura en Capas

La plataforma adopta una arquitectura en capas estricta. El flujo de una petición HTTP sigue exactamente este orden:

```
Cliente HTTP/WS
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA DE TRANSPORTE: FastAPI Router                     │
│  Responsabilidad: deserialización, validación Pydantic,  │
│  autenticación JWT, rate limiting, serialización         │
│  NO contiene lógica de negocio                          │
└─────────────────────────────┬───────────────────────────┘
                              │ llama a
                              ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA DE DOMINIO: Service                               │
│  Responsabilidad: lógica de negocio, orquestación,      │
│  validaciones de dominio, eventos de dominio            │
│  NO conoce HTTP (no usa Request/Response de FastAPI)    │
│  Lanza excepciones de dominio (DomainException),        │
│  NO excepciones HTTP                                    │
└─────────────────────────────┬───────────────────────────┘
                              │ llama a
                              ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA DE ACCESO A DATOS: Repository                     │
│  Responsabilidad: CRUD sobre modelos SQLAlchemy,        │
│  queries complejas, carga eager/lazy de relaciones      │
│  NO contiene lógica de negocio                          │
│  Trabaja con modelos ORM, devuelve modelos ORM          │
└─────────────────────────────┬───────────────────────────┘
                              │ usa
                              ▼
┌─────────────────────────────────────────────────────────┐
│  CAPA DE PERSISTENCIA: SQLAlchemy Models                │
│  Responsabilidad: mapeo ORM, constraints de DB,         │
│  definición de schemas, índices, relaciones             │
└─────────────────────────────────────────────────────────┘
```

### Reglas de la Arquitectura en Capas

1. **Las capas solo conocen la capa inmediatamente inferior.** Un Router nunca instancia un Repository directamente.
2. **Los Services no importan tipos de FastAPI.** `Request`, `Response`, `HTTPException` son conceptos del Router.
3. **Los Repositories reciben la AsyncSession por constructor injection (DI).** La sesión se inyecta desde las factories de dependencias o desde el Unit of Work, nunca se instancia dentro del repositorio.
4. **Las excepciones se transforman en la capa correcta.** `DomainException` → Router la convierte en `HTTPException`.

### Flujo de Ejemplo: Enviar Ejercicio

```
POST /api/v1/student/exercises/{id}/submit
    │
    ├── [Router] Valida JWT → extrae user_id
    ├── [Router] Valida body con SubmissionCreate schema (Pydantic)
    ├── [Router] Llama a submission_service.submit(user_id, exercise_id, code)
    │
    ├── [Service] Verifica que el estudiante está inscripto al curso
    ├── [Service] Verifica que el ejercicio pertenece a una comisión activa
    ├── [Service] Crea la submission y los snapshots de código
    ├── [Service] Emite evento SubmissionCreated al Event Bus
    ├── [Service] Retorna SubmissionDTO (no modelo ORM)
    │
    ├── [Router] Serializa SubmissionDTO → SubmissionResponse (Pydantic)
    └── [Router] Retorna HTTP 201
```

---

## 6. Schemas PostgreSQL y Reglas de Ownership

La base de datos utiliza 4 schemas PostgreSQL separados. Cada schema es propiedad exclusiva de una fase del sistema.

### Regla de Ownership

**Solo el owner de un schema puede escribir en sus tablas. Los demás dominios leen vía REST.**

Esta regla es un contrato arquitectural, no solo una convención. Se implementa mediante:
- Permisos de PostgreSQL (GRANT SELECT a otros roles, no GRANT INSERT/UPDATE/DELETE)
- Validación en los Services: un Service del dominio `cognitive` nunca importa repositorios del dominio `operational`

### Mapa de Schemas y Owners

```
┌─────────────────────────────────────────────────────────────────────┐
│  Schema: operational                                                │
│  Owner: Fases 0, 1 y 2 (auth, courses, exercises, tutor)           │
│  Tablas: users, courses, commissions, exercises, submissions,       │
│           code_snapshots, enrollments, tutor_interactions,          │
│           event_outbox                                              │
│  Readers: cognitive (via REST GET /api/v1/*)                       │
│  Nota: tutor_interactions pertenece a operational (escrita en F2)  │
├─────────────────────────────────────────────────────────────────────┤
│  Schema: cognitive                                                  │
│  Owner: Fase 3 ÚNICAMENTE (cognitive, evaluation)                   │
│  Tablas: cognitive_sessions, cognitive_events, reasoning_records,  │
│           cognitive_metrics                                         │
│  Readers: analytics, governance (via REST)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Schema: governance                                                 │
│  Owner: Fase 3 (governance)                                        │
│  Tablas: governance_events, tutor_system_prompts                   │
│  Readers: tutor (via REST — lee el prompt activo)                  │
├─────────────────────────────────────────────────────────────────────┤
│  Schema: analytics                                                  │
│  Owner: Fase 3 (analytics)                                         │
│  Tablas: risk_assessments                                          │
│  Readers: docentes via API                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Por Qué No Cross-Schema SQL Joins

Se podría hacer `SELECT * FROM operational.users JOIN cognitive.cognitive_sessions` directamente en SQL. Deliberadamente no lo hacemos:

1. **Acoplamiento de esquema**: un cambio en `operational.users` podría romper queries en `cognitive`.
2. **Ownership difuso**: ¿quién es responsable de ese join? ¿Qué índice lo optimiza?
3. **Testing**: los dominios se deben poder testear con DBs separadas en el futuro.
4. **Migración futura**: si cognitive se extrae a microservicio, los cross-schema joins son deuda técnica.

---

## 7. Estructura del Backend

```
backend/
├── pyproject.toml
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 001_create_operational_schema.py
│       ├── 002_create_cognitive_schema.py
│       ├── 003_create_governance_schema.py
│       └── 004_create_analytics_schema.py
│
└── app/
    ├── main.py              # Punto de entrada, registro de routers, CORS, lifespan
    ├── config.py            # Settings con Pydantic BaseSettings (env vars)
    ├── dependencies.py      # Fábrica de dependencias FastAPI reutilizables
    │
    ├── core/
    │   ├── security.py      # JWT encode/decode, hash de contraseñas (bcrypt)
    │   ├── exceptions.py    # DomainException y subclases (NotFound, Forbidden, etc.)
    │   └── logging.py       # Configuración structlog con request_id
    │
    ├── features/
    │   ├── auth/
    │   │   ├── router.py    # POST /auth/register, /login, /refresh, /logout
    │   │   ├── service.py   # AuthService: register, login, refresh_token
    │   │   ├── schemas.py   # RegisterRequest, LoginRequest, TokenResponse (Pydantic)
    │   │   └── dependencies.py  # get_current_user, require_role
    │   │
    │   ├── courses/
    │   │   ├── router.py    # CRUD /courses, /commissions, /enrollments
    │   │   ├── service.py   # CourseService, CommissionService
    │   │   └── schemas.py   # CourseCreate, CourseResponse, etc.
    │   │
    │   ├── exercises/
    │   │   ├── router.py    # CRUD /exercises, /submissions, /snapshots
    │   │   ├── service.py   # ExerciseService, SubmissionService
    │   │   └── schemas.py
    │   │
    │   ├── sandbox/
    │   │   ├── router.py    # POST /student/exercises/{id}/run
    │   │   ├── service.py   # SandboxService: ejecución aislada de código
    │   │   └── schemas.py   # RunRequest, RunResult
    │   │
    │   ├── tutor/
    │   │   ├── router.py    # WS /ws/tutor/chat, POST /reflection
    │   │   ├── service.py   # TutorService: streaming, guardrails
    │   │   ├── adapters.py  # LLMAdapter Protocol + AnthropicAdapter
    │   │   ├── guardrails.py # Políticas anti-solver
    │   │   └── schemas.py
    │   │
    │   ├── cognitive/
    │   │   ├── router.py    # /cognitive/sessions/*, /teacher/students/*
    │   │   ├── service.py   # CognitiveService: CTR, N4 scoring
    │   │   ├── hash_chain.py # HashChainService: SHA-256 chain
    │   │   └── schemas.py
    │   │
    │   ├── evaluation/
    │   │   ├── router.py    # /teacher/exercises/{id}/patterns
    │   │   ├── service.py   # EvaluationService: N1-N4 metrics
    │   │   └── schemas.py
    │   │
    │   └── governance/
    │       ├── router.py    # CRUD /admin/tutor/system-prompts
    │       ├── service.py   # GovernanceService
    │       └── schemas.py
    │
    └── shared/
        ├── db/
        │   ├── session.py       # AsyncSession factory, get_db dependency
        │   ├── base.py          # DeclarativeBase, TimestampMixin
        │   └── unit_of_work.py  # UnitOfWork context manager
        │
        ├── models/
        │   ├── operational.py   # User, Course, Commission, Exercise, Submission, etc.
        │   ├── cognitive.py     # CognitiveSession, CognitiveEvent, ReasoningRecord
        │   ├── governance.py    # GovernanceEvent, TutorSystemPrompt
        │   └── analytics.py     # RiskAssessment
        │
        ├── repositories/
        │   ├── base.py          # BaseRepository con operaciones CRUD genéricas
        │   ├── user_repo.py
        │   ├── course_repo.py
        │   ├── exercise_repo.py
        │   ├── submission_repo.py
        │   ├── tutor_repo.py
        │   ├── cognitive_repo.py
        │   ├── governance_repo.py
        │   └── analytics_repo.py
        │
        └── schemas/
            └── responses.py     # StandardResponse, PaginatedResponse wrappers
```

### Convenciones de Nomenclatura

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Archivos | snake_case | `cognitive_repo.py` |
| Clases | PascalCase | `CognitiveRepository` |
| Variables/funciones | snake_case | `get_student_profile()` |
| Constantes | UPPER_SNAKE | `MAX_RETRY_ATTEMPTS = 3` |
| Endpoints | kebab-case | `/cognitive/sessions/start` |
| Schema tables | snake_case | `cognitive_events` |

---

## 8. Estructura del Frontend

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts       # TailwindCSS 4 config
│
└── src/
    ├── main.tsx             # React 19 createRoot, Provider wrapper
    ├── App.tsx              # Router principal (React Router v7)
    │
    ├── features/
    │   ├── auth/
    │   │   ├── components/  # LoginForm, RegisterForm
    │   │   ├── hooks/       # useAuth, useAuthGuard
    │   │   ├── store/       # authStore (Zustand)
    │   │   ├── api/         # authApi (axios instance)
    │   │   └── types.ts     # User, TokenPair, AuthState
    │   │
    │   ├── student/
    │   │   ├── components/  # StudentDashboard, CourseCard, CourseList
    │   │   ├── hooks/       # useCourses, useEnrollment
    │   │   ├── store/       # studentStore
    │   │   ├── api/         # studentApi
    │   │   └── types.ts
    │   │
    │   ├── exercise/
    │   │   ├── components/  # ExerciseView, CodeEditor (Monaco), TestResults
    │   │   │               # TutorChat, MessageBubble, StreamingIndicator
    │   │   ├── hooks/       # useExercise, useSubmission, useCodeSnapshot
    │   │   │               # useTutorChat (WebSocket + streaming)
    │   │   ├── store/       # exerciseStore (código actual, resultados)
    │   │   │               # tutorStore (mensajes, estado WS)
    │   │   ├── ws/          # tutorWebSocket.ts (reconexión, heartbeat)
    │   │   ├── api/         # exerciseApi, sandboxApi
    │   │   └── types.ts
    │   │
    │   └── teacher/
    │       ├── components/  # TeacherDashboard, CognitiveDashboard, StudentProfile
    │       │               # TraceViewer, N4RadarChart, RiskAlert, PatternHeatmap
    │       ├── hooks/       # useCognitiveDashboard, useStudentTrace
    │       ├── store/       # teacherStore
    │       ├── api/         # teacherApi, cognitiveApi
    │       └── types.ts     # CognitiveSession, N4Score, RiskLevel
    │
    ├── shared/
    │   ├── components/      # Button, Input, Modal, Spinner, Table, Badge
    │   ├── hooks/           # useApiCall, usePagination, useDebounce
    │   ├── api/             # axiosInstance (interceptors JWT, retry)
    │   ├── types/           # StandardResponse, PaginatedResponse
    │   └── utils/           # formatDate, classNames, errorParser
    │
    └── styles/
        └── globals.css      # TailwindCSS 4 directivas + CSS custom properties
```

### Estructura de un Feature (Patrón)

Cada feature sigue la misma estructura interna. Esto permite que cualquier desarrollador navegue cualquier feature sin fricción:

```
features/[nombre]/
├── components/   → UI pura, recibe props, sin llamadas API directas
├── hooks/        → Lógica de UI, orquesta store + api
├── store/        → Estado Zustand 5, acciones, selectores
├── api/          → Funciones async que llaman al backend (sin estado)
└── types.ts      → Interfaces TypeScript del dominio
```

### Estado Global con Zustand 5

Cada feature tiene su propio slice de store. **No hay un store global monolítico.**

```typescript
// features/auth/store/authStore.ts
interface AuthState {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  setUser: (user: User) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isLoading: false,
      setUser: (user) => set({ user }),
      clearAuth: () => set({ user: null, accessToken: null }),
    }),
    { name: "auth-storage" }
  )
);
```

---

## 9. Patrones de Comunicación entre Fases

### 9.1 Event Bus Interno (Redis Streams)

El Event Bus desacopla las fases. Cuando el dominio `exercises` completa una entrega, emite un evento. El dominio `cognitive` consume ese evento para registrar la traza.

```
Fase 1 (exercises)          Redis Stream              Fase 3 (cognitive)
      │                    "events:submissions"              │
      │ SubmissionCreated  ──────────────────────────────>   │
      │                                                       │
      │                    "events:tutor"                    │
Fase 2 (tutor)             ──────────────────────────────>   │
      │ TutorInteraction                                      │
      │ Completed                                             │
```

**Contrato de evento (ejemplo)**:

```python
# shared/events.py
@dataclass
class SubmissionCreatedEvent:
    event_type: str = "submission.created"
    submission_id: UUID
    student_id: UUID
    exercise_id: UUID
    code: str
    timestamp: datetime
    correlation_id: UUID  # Para tracing distribuido
```

### 9.2 REST Contracts entre Dominios

Cuando un dominio necesita datos de otro, usa la API REST interna. No hay llamadas directas a repositorios de otro dominio.

```
cognitive/service.py                    exercises/router.py
        │                                       │
        │  GET /api/v1/exercises/{id}           │
        │ ─────────────────────────────────>    │
        │                                       │ (valida JWT interno)
        │  { exercise_id, title, topic }        │
        │ <─────────────────────────────────    │
```

**Por qué REST y no imports directos:**
- Mantiene el contrato explícito y versionado
- Permite evolucionar cada dominio de forma independiente
- Los tests de cognitive pueden mockear el endpoint de exercises

### 9.3 WebSocket para Tutor (Streaming)

El canal de chat con el tutor usa WebSocket nativo de FastAPI:

```
Frontend                Backend (FastAPI)           Anthropic API
    │                         │                           │
    │  WS: /ws/tutor/chat     │                           │
    │  ?token=<jwt>           │                           │
    │ ──────────────────────> │                           │
    │                         │  POST /messages (stream)  │
    │                         │ ────────────────────────> │
    │  { type: "token",       │                           │
    │    payload: {           │  SSE chunks               │
    │      text: "¿Qué..."}} │ <──────────────────────── │
    │ <────────────────────── │                           │
    │  { type: "complete",    │                           │
    │    payload: {...}}      │                           │
    │ <────────────────────── │                           │
```

---

## 10. Decisión Arquitectural: Monolito Modular vs. Microservicios

### Decisión: Monolito Modular

**Fecha de decisión**: 2025-Q4  
**Estado**: Vigente

### Contexto

La plataforma tiene 4 dominios de negocio (auth, core, tutor, cognitive) con lógica de dominio compleja. Se evaluaron dos alternativas:

**A) Microservicios desde el inicio**  
**B) Monolito Modular con separación por schemas**

### Por Qué se Eligió el Monolito Modular

#### 1. La complejidad está en el dominio, no en la infraestructura

El problema difícil de esta plataforma es:
- La cadena hash del CTR que debe ser consistente
- El modelo N4 que requiere correlacionar eventos de múltiples fases
- Las políticas de guardrails que deben evolucionar rápido

No es el escalado de peticiones HTTP (volumen universitario < 500 usuarios concurrentes).

#### 2. Costo de microservicios en etapa temprana

| Overhead | Microservicios | Monolito Modular |
|----------|---------------|-----------------|
| Distributed tracing | Necesario desde día 1 | Structlog + request_id |
| Service mesh | Kubernetes + Istio | No necesario |
| Data consistency | Saga / 2PC | Transacciones ACID |
| Deploys | CI/CD por servicio | Un deploy |
| Debugging | Logs distribuidos | Stack trace local |

En etapa universitaria/MVP, el overhead de microservicios consume tiempo de ingeniería que debería ir al dominio.

#### 3. Los schemas PostgreSQL son la frontera real

La separación por schemas cumple el mismo rol que los microservicios en términos de:
- **Ownership**: cada dominio escribe solo en su schema
- **Contratos**: los cross-domain accesses son explícitos (REST)
- **Evolución independiente**: las migraciones de Alembic son por schema

#### 4. Camino de extracción si es necesario

Si en el futuro el dominio `cognitive` necesita escalar independientemente:
1. El schema `cognitive` ya está separado → se mueve a su propia DB
2. Los REST contracts ya existen → se convierten en llamadas de red reales
3. Los eventos de Redis ya están desacoplados → se migran a Kafka

**No hay lock-in.** El monolito modular es microservicios listos para partir.

### Cuándo Revisar Esta Decisión

- Si el volumen supera los 5000 usuarios concurrentes
- Si los deploys de diferentes dominios se bloquean entre sí
- Si diferentes dominios necesitan stacks de lenguaje distintos
- Si el equipo supera 8 personas trabajando en paralelo en el mismo repo

---

*Documento generado: 2026-04-10 | Plataforma AI-Native v1.0*
