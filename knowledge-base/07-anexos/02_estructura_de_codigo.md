# Estructura de Código — Referencia Completa

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

## Visión General del Monorepo

```
ai-native-platform/
├── backend/           # FastAPI + SQLAlchemy 2.0 async
├── frontend/          # React 19 + Vite + Zustand 5 + TailwindCSS 4
├── shared/            # Contratos compartidos backend-frontend
├── infra/             # Docker Compose, scripts, seed data
├── devOps/            # Dockerfiles, scripts de CI/CD
├── knowledge-base/    # Documentación del proyecto (este directorio)
├── openspec/          # SDD: changes, specs (workflow OPSX)
├── scripts/           # Scripts utilitarios (seed, validate, migrate)
├── scaffold-decisions.yaml         # Fuente de verdad del scaffold
├── docker-compose.yml              # Servicios de infraestructura local
├── docker-compose.override.yml     # Overrides para desarrollo
├── env.example                    # Template de variables de entorno
├── .pre-commit-config.yaml         # Configuración de pre-commit hooks
├── Makefile                        # Comandos de conveniencia
└── .github/
    └── workflows/
        ├── ci.yml                  # Pipeline principal de CI
        └── adversarial-tests.yml   # Tests adversariales semanales
```

---

## Backend

### Árbol Completo

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, registro de routers y middleware
│   ├── config.py                   # Pydantic Settings, carga de variables de entorno
│   ├── dependencies.py             # Shared Depends() factories
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py             # JWT encode/decode, password hashing
│   │   ├── event_bus.py             # Event Bus basado en Redis Streams
│   │   ├── exceptions.py           # Excepciones de dominio (ExerciseNotFoundError, etc.)
│   │   └── logging.py              # Configuración de structlog
│   ├── features/
│   │   ├── auth/                   # Fase 0 — Login, registro, JWT, RBAC
│   │   │   ├── router.py           # /api/v1/auth/*
│   │   │   ├── service.py          # Login, logout, refresh, token management
│   │   │   ├── repository.py
│   │   │   ├── models.py           # User, UserRole — schema: operational
│   │   │   └── schemas.py          # LoginRequest, TokenResponse, RefreshRequest
│   │   ├── courses/                # Fase 1 — CRUD cursos, comisiones, enrollments
│   │   │   └── ...
│   │   ├── exercises/              # Fase 1 — CRUD ejercicios, submissions
│   │   │   ├── router.py           # /api/v1/exercises/*
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── models.py           # Exercise, TestCase — schema: operational
│   │   │   └── schemas.py
│   │   ├── sandbox/                # Fase 1 — Ejecución segura de código
│   │   │   ├── service.py          # subprocess con timeout 10s, 128MB RAM, sin red
│   │   │   └── schemas.py
│   │   ├── tutor/                  # Fase 2 — Orchestrator, guardrails, chat WS
│   │   │   ├── router.py           # WebSocket /ws/tutor/chat?token=<jwt> (exercise_id en init msg)
│   │   │   ├── service.py          # Sesiones de tutor, integración con Anthropic
│   │   │   ├── guardrails.py       # Pre/post processing para anti-solver
│   │   │   ├── prompt_builder.py   # Construcción de prompts socrátivos
│   │   │   └── schemas.py
│   │   ├── cognitive/              # Fase 3 — Event classifier, CTR builder, metrics
│   │   │   ├── router.py           # /api/v1/sessions/{id}/ctr/*
│   │   │   ├── service.py          # Creación y consulta de CTRs
│   │   │   ├── hash_chain.py       # HashChainService: SHA-256 chain para CTR (100% coverage)
│   │   │   ├── repository.py       # Solo create + read (no update, no delete)
│   │   │   ├── models.py           # CognitiveEvent — schema: cognitive (sin is_active)
│   │   │   └── schemas.py
│   │   ├── evaluation/             # Fase 3 — Evaluation engine, risk worker
│   │   │   ├── service.py          # Scoring N1-N4, Qe, métricas cognitivas
│   │   │   └── schemas.py
│   │   └── governance/             # Fase 3 — Audit, versioning, coherence
│   │       ├── router.py           # /api/v1/analytics/*
│   │       ├── service.py
│   │       ├── models.py           # GovernanceEvent — schema: governance (sin is_active)
│   │       └── schemas.py
│   └── shared/
│       ├── db/
│       │   ├── base.py             # DeclarativeBase, imports de todos los modelos
│       │   ├── session.py          # Engine, async_sessionmaker, get_db dependency
│       │   └── unit_of_work.py     # UoW pattern
│       ├── models/                 # Modelos SQLAlchemy compartidos (si aplica)
│       ├── repositories/
│       │   └── base_repository.py  # BaseRepository[T] con operaciones CRUD genéricas
│       └── schemas/
│           └── common.py           # SuccessResponse[T], ErrorResponse, PaginatedResponse[T]
├── alembic/
│   ├── env.py                      # Contexto de migración multi-schema
│   ├── script.py.mako              # Template para nuevas migraciones
│   └── versions/
│       ├── 0001_initial_schemas.py         # Crear 4 schemas PostgreSQL
│       ├── 0002_create_users_tables.py     # Tablas del schema operational
│       ├── 0003_create_cognitive_tables.py # Tablas del schema cognitive
│       ├── 0004_create_governance_tables.py # Tablas del schema governance
│       └── 0005_create_analytics_tables.py # Tablas del schema analytics
├── tests/
│   ├── conftest.py                 # Fixtures globales (engine, session, client, test users)
│   ├── factories.py                # Factory functions para crear objetos de test
│   ├── unit/
│   │   ├── test_hash_chain.py
│   │   ├── test_auth_service.py
│   │   ├── test_exercise_service.py
│   │   ├── test_sandbox_service.py
│   │   └── test_scoring_service.py
│   ├── integration/
│   │   ├── test_auth_router.py
│   │   ├── test_exercise_router.py
│   │   ├── test_session_router.py
│   │   └── test_ctr_router.py
│   └── adversarial/
│       ├── prompts.json            # 20+ prompts adversariales categorizados
│       └── test_tutor_guardrails.py
├── scripts/
│   └── seed_data.py               # Carga datos de prueba (usuarios, ejercicios demo)
├── pyproject.toml                 # Dependencias, configuración de ruff/mypy/pytest
└── alembic.ini                    # Configuración de Alembic (URL se lee del env)
```

### Archivos Clave — Descripciones Detalladas

**`app/main.py`**
El punto de entrada de la aplicación FastAPI. Crea la instancia de `FastAPI`, registra todos los routers con sus prefijos (`/api/v1/auth`, `/api/v1/exercises`, etc.), agrega middleware (CORS, logging, error handler), y configura el evento de startup (conectar a Redis, verificar DB).

**`app/core/config.py`**
Define `Settings(BaseSettings)` que carga todas las variables de entorno usando Pydantic Settings. Incluye validadores para valores críticos (SECRET_KEY no puede ser "CHANGE_ME" en producción). Se instancia como un singleton `settings = Settings()`.

**`app/features/cognitive/hash_chain.py`**
Implementa `HashChainService` con métodos `compute_genesis_hash()`, `compute_event_hash()` y `verify_chain()`. La serialización usa `json.dumps(sort_keys=True, separators=(",",":"))` para determinismo garantizado. Columnas en DB: `event_hash` y `previous_hash`.

**`app/db/session.py`**
Crea el `async_engine` usando `create_async_engine` con `asyncpg` como driver. Define `AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)`. Expone `get_db()` como FastAPI dependency que yield una sesión y la cierra al finalizar el request.

**`app/integrations/anthropic/guardrails.py`**
El módulo más crítico de la Fase 2. Implementa filtros de pre-procesamiento (detectar intenciones de solicitar solución) y post-procesamiento (detectar si la respuesta contiene código de solución). Usa heurísticas + un segundo llamado al LLM para clasificar casos ambiguos.

---

## Frontend

### Árbol Completo

```
frontend/
├── src/
│   ├── main.tsx                    # Entry point: ReactDOM.createRoot, StrictMode
│   ├── App.tsx                     # Router principal, layout global, theme provider
│   ├── app/
│   │   ├── router.tsx              # Definición de rutas con React Router
│   │   └── providers.tsx           # Wrapper de providers (QueryClient, ThemeProvider)
│   ├── features/
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.tsx       # Formulario de login con validación
│   │   │   │   ├── LogoutButton.tsx    # Botón de logout que llama al store
│   │   │   │   └── ProtectedRoute.tsx  # HOC que redirige al login si no autenticado
│   │   │   ├── hooks/
│   │   │   │   ├── useAuth.ts          # Hook que combina store y acciones de auth
│   │   │   │   └── useAuthRedirect.ts  # Hook para redirección post-login
│   │   │   ├── stores/
│   │   │   │   └── authStore.ts        # Zustand store: user, tokens, isAuthenticated
│   │   │   ├── api/
│   │   │   │   └── authApi.ts          # login(), logout(), refreshToken()
│   │   │   └── types.ts               # AuthUser, LoginRequest, TokenPair
│   │   ├── student/
│   │   │   ├── components/
│   │   │   │   ├── StudentDashboard.tsx # Dashboard del alumno: progreso N1-N4
│   │   │   │   └── ReflectionForm.tsx  # Formulario de reflexión post-sesión
│   │   │   ├── hooks/
│   │   │   │   └── useStudentProgress.ts
│   │   │   ├── stores/
│   │   │   │   └── studentStore.ts
│   │   │   ├── api/
│   │   │   │   └── studentApi.ts
│   │   │   └── types.ts
│   │   ├── teacher/
│   │   │   ├── components/
│   │   │   │   ├── TeacherDashboard.tsx  # Dashboard docente: vista de comisión
│   │   │   │   ├── CognitiveTimeline.tsx # Timeline de eventos cognitivos
│   │   │   │   ├── CTRDetail.tsx         # Detalle de un CTR específico
│   │   │   │   └── AIUsageIndicator.tsx  # Badge de tipo de uso (crítico/dependiente)
│   │   │   ├── hooks/
│   │   │   │   └── useTeacherReports.ts
│   │   │   ├── stores/
│   │   │   │   └── teacherStore.ts
│   │   │   ├── api/
│   │   │   │   └── teacherApi.ts
│   │   │   └── types.ts
│   │   ├── exercise/
│   │   │   ├── components/
│   │   │   │   ├── ExerciseList.tsx    # Lista paginada con filtros
│   │   │   │   ├── ExerciseCard.tsx    # Card individual de ejercicio
│   │   │   │   ├── ExerciseDetail.tsx  # Vista detalle de un ejercicio
│   │   │   │   ├── DifficultyFilter.tsx # Selector de nivel de dificultad
│   │   │   │   ├── CodeEditor.tsx      # Editor de código (Monaco)
│   │   │   │   ├── TutorChat.tsx       # Chat socrático con streaming
│   │   │   │   └── TestResults.tsx     # Resultado de evaluación de casos de test
│   │   │   ├── hooks/
│   │   │   │   ├── useExercises.ts     # Fetch + update del store al cargar ejercicios
│   │   │   │   ├── useExerciseDetail.ts
│   │   │   │   └── useTutorSession.ts  # Gestión del WebSocket, envío de mensajes
│   │   │   ├── stores/
│   │   │   │   ├── exerciseStore.ts    # exercises, filters, isLoading, error
│   │   │   │   └── tutorStore.ts       # messages, sessionId, wsStatus
│   │   │   ├── websocket/
│   │   │   │   └── tutorWebSocket.ts   # Clase TutorWebSocket con reconexión
│   │   │   ├── api/
│   │   │   │   └── exerciseApi.ts      # fetchExercises(), getExercise(), submitCode()
│   │   │   └── types.ts               # Exercise, ExerciseFilters, TutorMessage, SubmissionResult
│   │   └── shared/
│   │       ├── components/
│   │       │   ├── ErrorBoundary.tsx   # Error boundary a nivel feature
│   │       │   └── LoadingState.tsx
│   │       └── types.ts               # Tipos compartidos entre features
│   ├── shared/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx          # Botón con variantes (primary, secondary, ghost)
│   │   │   │   ├── Input.tsx           # Input con label, error, helper text
│   │   │   │   ├── Modal.tsx           # Modal con Headless UI
│   │   │   │   ├── Spinner.tsx         # Loading spinner
│   │   │   │   ├── Badge.tsx           # Badge de estado/nivel
│   │   │   │   ├── Pagination.tsx      # Controles de paginación
│   │   │   │   └── Toast.tsx           # Notificaciones toast
│   │   │   └── layout/
│   │   │       ├── AppLayout.tsx       # Layout con sidebar y header
│   │   │       ├── Sidebar.tsx         # Navegación lateral
│   │   │       └── Header.tsx          # Header con user menu
│   │   ├── hooks/
│   │   │   ├── useDebounce.ts          # Debounce para inputs de búsqueda
│   │   │   ├── useLocalStorage.ts      # Wrapper tipado de localStorage
│   │   │   └── useMediaQuery.ts        # Hook para responsive logic
│   │   ├── api/
│   │   │   ├── client.ts               # Axios instance con interceptors de auth
│   │   │   └── types.ts                # ApiResponse[T], PaginatedResponse[T], ApiError
│   │   └── utils/
│   │       ├── formatDate.ts           # Formateo de fechas ISO 8601
│   │       ├── formatDuration.ts       # Formateo de duraciones
│   │       └── cn.ts                   # Utility para combinar clases TailwindCSS
│   └── test/
│       ├── setup.ts                    # Setup global de Vitest (testing-library, mocks)
│       └── mocks/
│           ├── handlers.ts             # MSW handlers para mock de API
│           └── server.ts               # MSW server setup
├── e2e/
│   ├── auth.spec.ts                    # Tests E2E de autenticación
│   ├── exercise.spec.ts                # Tests E2E de ejercicios
│   └── tutor-session.spec.ts           # Tests E2E de sesión de tutor
├── public/
│   └── favicon.ico
├── index.html                          # Entry HTML de Vite
├── vite.config.ts                      # Configuración de Vite (proxy, plugins, test)
├── tailwind.config.ts                  # Tokens del design system, plugins
├── tsconfig.json                       # TypeScript config (strict: true)
├── tsconfig.node.json                  # TypeScript config para vite.config.ts
├── eslint.config.ts                    # ESLint flat config (v9)
├── .prettierrc                         # Configuración de Prettier
└── playwright.config.ts               # Configuración de Playwright E2E

```

### Archivos Clave del Frontend — Descripciones

**`src/shared/api/client.ts`**
Instancia de Axios configurada con:
- `baseURL: \`${import.meta.env.VITE_API_URL}/api/v1\``
- Interceptor de request: agrega `Authorization: Bearer {token}` desde el authStore
- Interceptor de response: en error 401, intenta refresh del token; si falla, logout
- Interceptor de response: convierte snake_case a camelCase automáticamente (axios-case-converter)

**`src/features/exercise/websocket/tutorWebSocket.ts`**
Clase que encapsula la conexión WebSocket con el tutor. Maneja:
- Conexión con token en query param
- Reconexión con backoff exponencial (máximo 5 intentos)
- Respuesta a pings del servidor
- Emisión de eventos al store de Zustand

**`src/app/router.tsx`**
Define las rutas usando React Router v7. Todas las rutas están envueltas en `ProtectedRoute` excepto `/login`. Usa `lazy()` para code splitting de cada feature.

---

## Shared

```
shared/
├── types/
│   └── api.ts          # Tipos compartidos que deben coincidir exactamente
│                        # entre backend (Pydantic) y frontend (TypeScript)
│                        # En la práctica, los tipos se definen en el backend
│                        # y se generan/sincronizan al frontend.
└── constants/
    └── cognitive.ts    # Constantes del dominio compartidas (nombres de niveles N1-N4)
```

**Propósito del directorio `shared/`**: Evitar que los contratos de API se desincronicen. Los tipos de respuesta definidos aquí deben ser la fuente de verdad. En la práctica, se pueden generar desde el schema OpenAPI del backend.

---

## Infra

```
infra/
├── docker-compose.yml       # Servicios de infraestructura local (postgres, redis, pgadmin)
├── docker-compose.prod.yml  # Overrides para producción
├── nginx/                   # Configuración de nginx como reverse proxy
│   └── nginx.conf           # Proxy a backend:8000 y frontend:5173, WebSocket upgrade
├── scripts/
│   ├── deploy.sh            # Script de deploy al servidor de UTN FRM
│   ├── backup_db.sh         # Backup de PostgreSQL
│   └── health_check.sh      # Verificación de salud post-deploy
└── seed/
    └── seed_data.py         # Datos iniciales de prueba
```

El `nginx.conf` es crítico para el deploy en el servidor institucional: maneja el routing entre el frontend estático y el backend, y la configuración de WebSocket upgrade para el tutor.

---

## DevOps

```
devOps/
├── Dockerfile.backend               # Multi-stage: build (deps) → runtime
├── Dockerfile.frontend              # Multi-stage: build (vite) → nginx para servir estáticos
├── .dockerignore
└── scripts/
    ├── deploy.sh                    # Script de deploy al servidor de UTN FRM
    ├── backup_db.sh                 # Backup de PostgreSQL a almacenamiento local
    └── health_check.sh              # Verificación de salud post-deploy
```

**`Dockerfile.backend`**: Imagen Python 3.12 slim. Instala dependencias en una capa separada (para cache de Docker). No incluye herramientas de dev. El entrypoint corre `uvicorn app.main:app`.

**`Dockerfile.frontend`**: Dos stages: Node 20 para el build de Vite, luego nginx alpine para servir los archivos estáticos del `dist/`. El nginx también sirve como SPA router (todas las rutas sirven `index.html`).
