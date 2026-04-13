# EPIC-06: Gestión de Ejercicios

> **Issue**: #6 | **Milestone**: Fase 1 — Core Académico | **Labels**: epic, fase-1, priority:critical

## Contexto

Los ejercicios son el núcleo de la interacción alumno-plataforma. Cada ejercicio tiene enunciado, starter code, test cases, y metadata (dificultad, topics). El docente los crea y gestiona dentro de una comisión; el alumno los ve y resuelve. Cuando un alumno abre el detalle de un ejercicio se emite el evento `reads_problem` — el punto de entrada N1 para la trazabilidad cognitiva de Fase 3.

## Alcance

### Backend
- Modelo SQLAlchemy: `exercises` con JSONB para `test_cases` y `TEXT[]` para `topic_tags`
- Repository con filtros avanzados (por comisión, dificultad, topic, búsqueda)
- Domain service: `ExerciseService`
- Endpoints REST:
  - `GET/POST /api/v1/courses/{id}/exercises` (docente crea, alumno lista)
  - `GET/PUT/DELETE /api/v1/exercises/{id}` (docente gestiona, alumno ve detalle)
  - `GET /api/v1/student/exercises` (alumno — ejercicios de mis comisiones con filtros)
- Al responder `GET /api/v1/exercises/{id}` para un alumno autenticado, el backend emite el evento `reads_problem` al Event Bus
- Validación de test_cases schema (JSONB con estructura definida)
- Índice GIN sobre `topic_tags` para búsqueda eficiente

### Frontend
- **Docente**: ABM de ejercicios (crear con markdown editor para enunciado, definir test cases, starter code)
- **Alumno**: listado de ejercicios con filtros (dificultad, topic, estado) + vista detalle del enunciado
- MSW handlers

## Contratos

### Produce
- Endpoints REST de ejercicios
- Modelo `exercises` en schema `operational`
- Datos de ejercicio que EPIC-07 (sandbox) y EPIC-08 (submissions) consumen
- Evento: `reads_problem` (stream: `events:submissions`) — emitido cuando un alumno abre el detalle de un ejercicio. Payload: `{ student_id, exercise_id, course_id, timestamp }`

### Consume
- Cursos (de EPIC-05) — los ejercicios pertenecen a cursos (course_id FK). Las comisiones son el contexto de enrollment, no de ownership de ejercicios
- Auth y RBAC (de EPIC-03)
- DB patterns (de EPIC-02)

### Modelos (owner — schema: operational)
- `exercises`: id (UUID PK), course_id (FK → courses.id, NOT NULL), title (VARCHAR 255), description (TEXT), test_cases (JSONB) -- Estructura completa:
  ```json
  {
    "language": "python",
    "timeout_ms": 10000,
    "memory_limit_mb": 128,
    "cases": [
      {
        "id": "tc-001",
        "description": "Caso base",
        "input": "...",
        "expected_output": "...",
        "is_hidden": false,
        "weight": 1.0
      }
    ]
  }
  ```, difficulty (ENUM: easy/medium/hard), topic_tags (TEXT[], NOT NULL, DEFAULT '{}'), language (VARCHAR 50, default 'python'), starter_code (TEXT, default ''), max_attempts (SMALLINT, default 10), time_limit_minutes (SMALLINT, default 60), order_index (SMALLINT, default 0), is_active (BOOL), created_at, updated_at

## Dependencias
- **Blocked by**: EPIC-05 (ejercicios pertenecen a cursos)
- **Blocks**: EPIC-07 (sandbox ejecuta código de ejercicios), EPIC-08 (submissions referencian ejercicios), EPIC-09 (tutor necesita contexto del ejercicio)

## Stories

- [ ] Modelo SQLAlchemy: exercises con course_id FK, topic_tags TEXT[], campos completos + migración Alembic
- [ ] Índice GIN sobre `topic_tags` para búsqueda eficiente
- [ ] ExerciseRepository con filtros (comisión, dificultad, topic, búsqueda full-text)
- [ ] ExerciseService con validación de negocio
- [ ] Endpoints REST: CRUD ejercicios bajo `/api/v1/courses/{id}/exercises` (docente) + listado/detalle (alumno)
- [ ] Emisión del evento `reads_problem` al Event Bus cuando alumno accede al detalle de un ejercicio
- [ ] Validación de schema JSONB para test_cases
- [ ] Frontend docente: ABM ejercicios (markdown editor, test cases builder, starter code)
- [ ] Frontend alumno: listado con filtros + vista detalle enunciado
- [ ] MSW handlers
- [ ] Tests de integración: CRUD + filtros + RBAC + emisión del evento reads_problem

## Criterio de Done

- Docente puede crear ejercicios con enunciado markdown, starter code y test cases dentro de una comisión
- Alumno puede listar ejercicios de sus comisiones con filtros y ver el detalle
- Al abrir el detalle de un ejercicio se emite el evento `reads_problem` al Event Bus
- Test cases validados en estructura JSONB
- Búsqueda por `topic_tags` usa índice GIN
- Tests de integración pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/01-negocio/04_reglas_de_negocio.md`
