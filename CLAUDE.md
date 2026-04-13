# Plataforma AI-Native

> Canonical file. `AGENTS.md` is the model-agnostic version. Modify one → update the other.

## Visión del Proyecto

Sistema pedagógico-tecnológico para enseñanza de programación universitaria (UTN FRM). Integra un tutor IA socrático que guía sin dar respuestas, un registro estructurado del proceso cognitivo del alumno (CTR — Cognitive Trace Record), evaluación multidimensional basada en el modelo N4, y un marco de gobernanza que garantiza coherencia entre el modelo teórico doctoral y la implementación técnica.

**Problema**: La IA generativa rompió la relación entre el código que un alumno entrega y lo que realmente aprendió. El código ya no es evidencia confiable de aprendizaje.

**Solución**: Pasar de evaluar productos (`E = correctness(output)`) a observar procesos cognitivos (`E = f(N1, N2, N3, N4, Qe)`).

**Modelo N4** (niveles de observación cognitiva):
- **N1 — Comprensión**: ¿El alumno entiende el problema?
- **N2 — Estrategia**: ¿El alumno puede planificar una solución?
- **N3 — Validación**: ¿El alumno verifica y corrige su razonamiento?
- **N4 — Interacción con IA**: ¿El alumno usa la IA críticamente o como oráculo?

## Tech Stack

| Componente | Puerto | Tecnología |
|-----------|--------|-----------|
| Backend API | 8000 | Python 3.12 + FastAPI + SQLAlchemy 2.0 async |
| Frontend | 5173 | React 19 + TypeScript + Zustand 5 + TailwindCSS 4 + Vite |
| Base de datos | 5432 | PostgreSQL 16 (schemas: operational, cognitive, governance, analytics) |
| Cache | 6379 | Redis 7 |
| LLM | — | Anthropic API (Claude) |

**Prerequisitos**: Python 3.12+, Node.js 20+, Docker + Docker Compose, PostgreSQL 16, Redis 7
**Variables críticas**: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `SECRET_KEY`

## Modelo de Datos (resumen)

```
[Schema: operational]
Course → Commission (1:N)
Commission → Enrollment ← Student (M:N)
Course → Exercise (1:N)
Exercise → Submission ← Student (M:N)
Submission → CodeSnapshot (1:N)

[Schema: cognitive]
Student + Exercise → CognitiveSession (1:N)
CognitiveSession → CognitiveEvent (1:N, hash-chained CTR)
CognitiveSession → CognitiveMetrics (1:1)
CognitiveSession → ReasoningRecord (1:N)
Student → RiskAssessment (1:N)

[Schema: operational — owner: Fase 2]
Student + Exercise → TutorInteraction (1:N, dentro de CognitiveSession)

[Schema: governance]
TutorSystemPrompt (versionado con SHA-256)
GovernanceEvent (policy violations, prompt updates, model changes)

NOTA: Fase 2 escribe en operational (tutor_interactions). Fase 2 NO escribe en cognitive.
El schema cognitive es owned EXCLUSIVAMENTE por Fase 3.
```

Detalle: `knowledge-base/02-arquitectura/02_modelo_de_datos.md`

## Arquitectura

```
Router (thin — HTTP/WS only)
  → Domain Service (lógica de negocio, validación, orquestación)
    → Repository (acceso a datos, queries)
      → Model (SQLAlchemy)
```

**Patrón backend**: Modular por dominio. Cada fase es dueña de su schema PostgreSQL. Solo la fase dueña puede INSERT/UPDATE/DELETE. Otras fases leen via REST, nunca queries directos a tablas ajenas.

**Patrón frontend**: Feature folders (`/features/student/`, `/features/teacher/`, `/features/exercise/`, `/features/auth/`).

**Patrones de diseño**: Repository, Unit of Work, Event Bus (entre fases), Hash Chain (CTR).

### Componentes del sistema

| Componente | Responsabilidad | Fase |
|-----------|----------------|------|
| Tutor Orchestrator | Construye contexto, compone prompt, controla flujo socrático | Fase 2 |
| AI Gateway | Conexión con LLM, control de prompts, logging | Fase 2 |
| Moderador Pedagógico | Guardrails anti-solver, detecta soluciones directas | Fase 2 |
| Cognitive Trace Engine | Registra eventos, construye CTR, clasifica N1-N4 | Fase 3 |
| Cognitive Analytics Engine | Interpreta CTR, calcula métricas, infiere calidad epistémica | Fase 3 |
| Evaluation Engine | Aplica función evaluativa E = f(N1,N2,N3,N4,Qe) | Fase 3 |
| Governance Layer | Auditoría, versionado, coherencia semántica | Fase 3 |

## Reglas Críticas — No Negociables

### Backend (FastAPI + SQLAlchemy)

**Router Layer**
1. Routers son THIN — HTTP in, HTTP out. Cero lógica de negocio.
2. Toda ruta recibe un domain service via `Depends()`.
3. Funciones de ruta: validar input (Pydantic), llamar service, retornar response. Nada más.
4. Usar `status_code=` como parámetro, nunca hardcodear status en el body.
5. Path params para identidad del recurso, query params para filtros, body para mutaciones.
6. Paginación: `page`/`per_page` con máximos sensatos, nunca queries sin límite.

**Domain Service Layer**
7. TODA lógica de negocio vive en domain services — validación, autorización, orquestación.
8. Services reciben repositories via inyección en constructor, nunca los instancian.
9. Services NUNCA importan `AsyncSession` — solo hablan con repositories.
10. Services retornan objetos de dominio o lanzan excepciones de dominio, nunca HTTPException.
11. Llamadas cross-service van por la capa de servicios, nunca repository-to-repository.

**Repository Layer**
12. `db.commit()` NUNCA se llama directo — usar Unit of Work.
13. `Model.is_active == True` está MAL — usar `Model.is_active.is_(True)`.
14. SIEMPRE usar `selectinload()` / `joinedload()` para relaciones — prevenir N+1.
15. `with_for_update()` para cualquier patrón read-then-write (race conditions).
16. NUNCA retornar `None` silenciosamente — raise o usar Optional explícitamente.

**Session & Transaction**
17. Una `AsyncSession` por request via dependency injection.
18. `expire_on_commit=False` en session factory — previene lazy load errors post-commit.
19. Transacciones anidadas con `session.begin_nested()` para rollbacks parciales.
20. NUNCA mezclar sesiones sync y async — async en todo el proyecto.

**General**
21. Logging estructurado via logger del proyecto, NUNCA `print()`.
22. Pydantic v2 para TODOS los boundaries de API — `model_config = ConfigDict(from_attributes=True)`.
23. Soft delete via `is_active: bool` o `deleted_at: datetime | None` — hard delete solo para registros efímeros. **Excepción**: eventos del CTR y `code_snapshots` son inmutables (evidencia de proceso, no se pueden modificar ni eliminar).
24. Alembic auto-generate para migraciones, siempre revisar antes de aplicar.
25. Formato de respuesta estándar: `{ status: "ok"|"error", data: {}, meta: { page, total, per_page, total_pages }, errors: [{ code, message, field }] }`.

### Reglas del Dominio AI-Native

26. El tutor NUNCA entrega soluciones completas. Máximo 5 líneas de código parcial y contextual.
27. Toda evaluación se deriva del modelo N4: `E = f(N1, N2, N3, N4, Qe)`. NUNCA `E = correctness(output)`.
28. Todo evento cognitivo incluye contexto (tiempo, problema, estado del estudiante). No hay dato sin contexto.
29. Toda interacción con IA se registra: prompt, respuesta, clasificación N4.
30. Cada turno del tutor incluye SHA-256 del prompt vigente para reconstrucción criptográfica.
31. El CTR es inmutable post-cierre. Hash encadenado: `hash(n) = SHA256(hash(n-1) + datos(n))`.
32. Solo la fase dueña de un schema puede INSERT/UPDATE/DELETE. Otras fases leen via REST.

### Frontend (React 19 + Zustand 5 + TailwindCSS 4)

**Zustand Store**
1. NUNCA destructurar el store — usar selectores individuales.
2. SIEMPRE `useShallow()` para selectores de objetos/arrays — previene rerenders innecesarios.
3. SIEMPRE referencias de fallback estables — `const EMPTY: T[] = []` fuera del componente, nunca inline `[]`.
4. Un store por dominio acotado — `useExerciseStore`, `useAuthStore`, `useCognitiveStore`, no un god store.
5. Estado derivado via selectores, NUNCA almacenado redundantemente.
6. Actions son funciones dentro del store, NUNCA funciones standalone que llaman `setState`.

**Componentes**
7. Preferir `use()` (React 19) para resolución de promesas sobre useEffect + useState.
8. Error boundaries a nivel feature — un componente roto no crashea la app.
9. Keys en listas dinámicas: IDs estables, NUNCA índices de array.
10. Side effects en `useEffect` solamente, NUNCA durante render.
11. Form state: inputs controlados con state local o React Hook Form, NO Zustand.

**WebSocket (streaming del tutor)**
12. Conexiones WebSocket via ref pattern — dos `useEffect`s separados.
13. SIEMPRE retornar cleanup de efectos WebSocket.
14. Reconexión con exponential backoff — nunca retry infinito a velocidad completa.
15. Mensajes WS actualizan store via actions, NUNCA setState directo.

**TypeScript**
16. IDs son `string` en frontend, aunque sean `UUID` en backend — convertir en el boundary.
17. Respuestas API tipadas con Zod schemas, no bare `as Type` casts.
18. Discriminated unions para state machines — `{ status: 'loading' } | { status: 'ready', data: T }`.

**Styling (TailwindCSS 4)**
19. Design tokens via CSS custom properties en `@theme` — nunca hex hardcodeados.
20. Dark mode via `dark:` variant con swap de CSS variables.
21. Responsive: mobile-first con `sm:`, `md:`, `lg:` breakpoints.
22. Mobile containers: `overflow-x-hidden w-full max-w-full` — previene scroll horizontal.
23. Logger centralizado, NUNCA `console.*` directamente.

## Convenciones

- **Idioma UI**: Español | **Código**: Inglés
- **IDs**: `string` frontend, `UUID` backend
- **Naming**: Frontend `camelCase`, Backend `snake_case`
- **Timestamps**: ISO 8601 con timezone UTC (`2026-04-09T14:30:00Z`)
- **Paginación**: query params `?page=1&per_page=20`, respuesta en `meta`
- **Filtros**: query params `snake_case` (`?student_id=xxx&status=active`)
- **Errores HTTP**: 400 validación, 401 no autenticado, 403 no autorizado, 404 no encontrado, 422 entidad no procesable, 500 error interno
- **Commits**: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- **Branching**: GitHub Flow (feature branches → main)

## Auth (resumen)

| Contexto | Método | Header / Mecanismo |
|---------|--------|-------------------|
| Alumno / Docente / Admin | JWT (access 15min + refresh 7d, rotation) | `Authorization: Bearer <token>` |
| WebSocket (tutor) | JWT | Query param `?token=` en handshake |

**Roles**: alumno, docente, admin
**Rate limiting**: 30 msg/hora por alumno al tutor **por ejercicio**, 100 req/min general
**Token storage**: access token en Zustand memory, refresh token en httpOnly cookie

Detalle: `knowledge-base/03-seguridad/01_modelo_de_seguridad.md`

## RBAC

| Rol | Cursos | Ejercicios | Submissions | Tutor | Métricas Cognitivas | Traza CTR | Governance |
|-----|--------|-----------|-------------|-------|-------------------|-----------|-----------|
| alumno | ver propios | ver + resolver | crear + ver propias | chatear | ver propias (scores agregados) | — | — |
| docente | gestionar | gestionar | ver todas (su comisión) | ver sesiones (su comisión) | ver todas (su comisión) | ver (su comisión) | ver reportes |
| admin | gestionar todo | gestionar todo | ver todas | ver sesiones (todas) | ver todas | ver todas | gestionar todo |

## Gobernanza de Cambios

- **CRITICAL** (Auth, CTR hash chain, Evaluation Engine, guardrails del tutor): solo análisis, no cambiar sin revisión
- **HIGH** (motor cognitivo, clasificador N4, schemas de DB): proponer y esperar revisión
- **MEDIUM** (CRUD operacional, frontend views): implementar con checkpoints
- **LOW** (catálogos, config, seeds): autonomía total si los tests pasan

### Gobernanza del Documento Maestro (empate3)

- Cambio mayor (X.0): modifica constructo estable (niveles N1-N4) → revisión formal con manuscrito doctoral
- Cambio menor (X.Y): modifica constructo operativo provisional (umbrales CTR, mapeo event_type → N4) → aprobación del responsable institucional
- Cambio de refinamiento (X.Y.Z): ajusta constructo en refinamiento (dependency score, calidad epistémica) → fundamentación escrita

## Decisiones Arquitectónicas Clave

- **Monolito modular** en vez de microservicios — la complejidad está en el dominio, no en la infra
- **4 schemas PostgreSQL** (operational, cognitive, governance, analytics) — ownership por fase, lectura cruzada via REST
- **Hash chain en CTR** — inmutabilidad y auditabilidad del registro cognitivo
- **WebSocket para streaming del tutor** — respuestas token por token, UX conversacional
- **Sandbox aislado para ejecución de código** — subprocess con timeout 10s, 128MB RAM, sin red, sin filesystem fuera de /tmp
- **SHA-256 del prompt en cada interacción** — reconstrucción criptográfica del contexto exacto del tutor
- **Event bus entre fases (Redis Streams)** — desacople de producción/consumo de eventos cognitivos
- **MSW para desarrollo paralelo del frontend** — mocks basados en OpenAPI spec, se remueve en integración

## Mapa de Navegación

| Necesito... | Leer |
|------------|------|
| Entender el sistema y su visión | `knowledge-base/01-negocio/01_vision_y_contexto.md` |
| Ver los actores y roles | `knowledge-base/01-negocio/02_actores_y_roles.md` |
| Ver features y EPICs | `knowledge-base/01-negocio/03_features_y_epics.md` |
| Reglas de negocio del dominio | `knowledge-base/01-negocio/04_reglas_de_negocio.md` |
| Flujos principales | `knowledge-base/01-negocio/05_flujos_principales.md` |
| Backlog priorizado | `knowledge-base/01-negocio/06_backlog.md` |
| Arquitectura general | `knowledge-base/02-arquitectura/01_arquitectura_general.md` |
| Modelo de datos completo | `knowledge-base/02-arquitectura/02_modelo_de_datos.md` |
| API y endpoints | `knowledge-base/02-arquitectura/03_api_y_endpoints.md` |
| Patrones de diseño | `knowledge-base/02-arquitectura/04_patrones_de_diseno.md` |
| Eventos y WebSocket | `knowledge-base/02-arquitectura/05_eventos_y_websocket.md` |
| Abstracciones y contratos | `knowledge-base/02-arquitectura/06_abstracciones_y_contratos.md` |
| ADRs (Architecture Decision Records) | `knowledge-base/02-arquitectura/07_adrs.md` |
| Modelo de seguridad | `knowledge-base/03-seguridad/01_modelo_de_seguridad.md` |
| Superficie de ataque | `knowledge-base/03-seguridad/02_superficie_de_ataque.md` |
| Configuración de entorno | `knowledge-base/04-infraestructura/01_configuracion.md` |
| Dependencias | `knowledge-base/04-infraestructura/02_dependencias.md` |
| Deploy | `knowledge-base/04-infraestructura/03_deploy.md` |
| Migraciones | `knowledge-base/04-infraestructura/04_migraciones.md` |
| Integraciones externas | `knowledge-base/04-infraestructura/05_integraciones.md` |
| Onboarding de desarrollador | `knowledge-base/05-dx/01_onboarding.md` |
| Tooling y ambiente | `knowledge-base/05-dx/02_tooling.md` |
| Trampas conocidas | `knowledge-base/05-dx/03_trampas_conocidas.md` |
| Convenciones y estándares | `knowledge-base/05-dx/04_convenciones_y_estandares.md` |
| Workflow de implementación | `knowledge-base/05-dx/05_workflow_implementacion.md` |
| Estrategia de testing | `knowledge-base/05-dx/06_estrategia_de_testing.md` |
| Roadmap | `knowledge-base/06-estado/01_roadmap.md` |
| Preguntas y suposiciones | `knowledge-base/06-estado/02_preguntas_y_suposiciones.md` |
| Salud del proyecto | `knowledge-base/06-estado/03_salud_del_proyecto.md` |
| Deuda técnica | `knowledge-base/06-estado/04_deuda_tecnica.md` |
| Inconsistencias | `knowledge-base/06-estado/05_inconsistencias.md` |
| Referencia de skills | `knowledge-base/07-anexos/01_referencia_skills.md` |
| Estructura de código | `knowledge-base/07-anexos/02_estructura_de_codigo.md` |
| Glosario del dominio | `knowledge-base/07-anexos/03_glosario.md` |
| Historias de usuario | `Historias de Usuario.md` |
| Metodología GitHub | `metodologia_github.md` |
| Guía de desarrollo | `guia_desarrollo.md` |
| Contribución | `CONTRIBUTING.md` |

## Estructura del Repositorio

```
ai-native/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── dependencies.py            # Shared Depends() factories
│   │   ├── core/
│   │   │   ├── security.py            # JWT, password hashing (bcrypt)
│   │   │   ├── exceptions.py          # Domain exceptions
│   │   │   └── logging.py             # Structured JSON logger
│   │   ├── features/
│   │   │   ├── auth/                  # Fase 0 — Login, registro, JWT, RBAC
│   │   │   ├── courses/               # Fase 1 — CRUD cursos, comisiones, enrollments
│   │   │   ├── exercises/             # Fase 1 — CRUD ejercicios, submissions
│   │   │   ├── sandbox/               # Fase 1 — Ejecución segura de código
│   │   │   ├── tutor/                 # Fase 2 — Orchestrator, guardrails, chat WS
│   │   │   ├── cognitive/             # Fase 3 — Event classifier, CTR builder, metrics
│   │   │   ├── evaluation/            # Fase 3 — Evaluation engine, risk worker
│   │   │   └── governance/            # Fase 3 — Audit, versioning, coherence
│   │   └── shared/
│   │       ├── db/
│   │       │   ├── session.py         # AsyncSession factory
│   │       │   ├── base.py            # DeclarativeBase
│   │       │   └── unit_of_work.py    # UoW pattern
│   │       ├── models/                # SQLAlchemy models por schema
│   │       ├── repositories/          # Base + concrete repos
│   │       └── schemas/               # Pydantic schemas compartidos
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── prompts/                       # System prompts versionados del tutor
│   │   └── socratic_tutor_system.md
│   ├── rubrics/                       # Rúbricas N4
│   │   └── n4_anexo_b.yaml
│   ├── tests/
│   │   ├── conftest.py                # Fixtures: async session, test client
│   │   ├── integration/
│   │   ├── unit/
│   │   └── adversarial/               # Tests adversarios contra el tutor
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                    # Router + providers
│   │   ├── config.ts                  # Env vars, API URLs
│   │   ├── features/
│   │   │   ├── auth/                  # Login, registro
│   │   │   ├── student/               # Dashboard alumno, vista ejercicio, reflexión
│   │   │   ├── teacher/               # Dashboard docente, traza cognitiva, reportes
│   │   │   ├── exercise/              # Monaco editor, ejecución, submission
│   │   │   └── shared/                # Componentes compartidos
│   │   ├── shared/
│   │   │   ├── components/            # Button, Modal, DataTable, RadarChart
│   │   │   ├── hooks/                 # useDebounce, useWebSocket, useAuth
│   │   │   ├── lib/                   # Logger, API client, formatters
│   │   │   └── types/                 # Shared types, API response wrappers
│   │   └── styles/
│   │       └── globals.css            # @theme, @layer, Tailwind base
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── shared/                            # Schemas compartidos, tipos, contratos OpenAPI
├── infra/                             # Docker Compose, scripts, seed data
├── devOps/                            # Docker, nginx, monitoring, backup
├── knowledge-base/                    # Documentación de dominio + arquitectura
├── openspec/                          # SDD: changes, specs
├── scaffold-decisions.yaml            # Fuente de verdad del scaffold
└── .env.example
```

## Claude Code Integration

### Skills Disponibles

| Skill | Trigger |
|-------|---------|
| `fastapi-domain-service` | Trabajando en routers, services o dependencies de FastAPI |
| `sqlalchemy-patterns` | Trabajando con modelos, repositories o queries SQLAlchemy |
| `zustand-store-pattern` | Trabajando con stores Zustand, selectores o actions |
| `tailwind-theme-system` | Trabajando con estilos, dark mode o responsive |
| `redis-best-practices` | Trabajando con Redis: cache, event bus, TTL |
| `websocket-patterns` | Trabajando con WebSocket: streaming del tutor, conexiones |
| `api-security` | Trabajando con auth, JWT, rate limiting, RBAC |

### Workflow OPSX

- `/opsx:explore` — Pensar antes de comprometerse
- `/opsx:propose` — Crear change con artefactos
- `/opsx:apply` — Implementar tasks
- `/opsx:verify` — Validar implementación
- `/opsx:archive` — Cerrar change

## Reglas

- Nunca agregar atribución de IA en commits. Solo Conventional Commits.
- Nunca buildear después de cambios salvo que se pida explícitamente.
- Al hacer una pregunta, PARAR y esperar respuesta.
- Nunca aceptar claims del usuario sin verificación.
- Nunca commitear o pushear salvo que se pida explícitamente.
- Usar `/opsx:*` para el workflow de spec-driven development.
