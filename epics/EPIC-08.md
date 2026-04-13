# EPIC-08: Submission Flow y Code Snapshots

> **Issue**: #8 | **Milestone**: Fase 1 — Core Académico | **Labels**: epic, fase-1, priority:critical

## Contexto

El flujo completo de cómo un alumno trabaja en un ejercicio: escribe código, ejecuta, itera, y finalmente envía su solución. Los code snapshots capturan el proceso de escritura (cada 30s + ante ejecución) — son EVIDENCIA de proceso cognitivo, inmutables, nunca se eliminan.

## Alcance

### Backend
- Modelos SQLAlchemy: `submissions`, `code_snapshots`
- Domain service: `SubmissionService`, `SnapshotService`
- Endpoints REST:
  - `POST /api/v1/exercises/{id}/submissions` — crear submission
  - `PUT /api/v1/submissions/{id}/submit` — enviar (cambia status a passed/failed/error)
  - `GET /api/v1/student/submissions` — mis submissions
  - `GET /api/v1/submissions/{id}` — detalle con test results
  - `POST /api/v1/exercises/{id}/snapshots` — guardar snapshot
- Submission flow: `pending` → `running` → `passed` / `failed` / `error`
- Code snapshots automáticos (sin edit_distance — no es parte del modelo)
- Submissions usan el SandboxService de EPIC-07 para ejecutar
- Atributo `attempt_number` se incrementa por alumno+ejercicio en cada nueva submission

### Frontend
- Monaco Editor integrado en la vista de ejercicio:
  - Syntax highlighting Python
  - Auto-save (snapshot cada 30s)
  - Snapshot ante cada ejecución
- Botón "Enviar Solución" (submit final)
- Historial de submissions del alumno por ejercicio
- **Docente**: ver submissions de alumnos de su comisión

## Contratos

### Produce
- Endpoints REST de submissions y snapshots
- Modelos `submissions`, `code_snapshots` en schema `operational`
- Eventos (para Event Bus → Fase 3):
  - `exercise.submitted` (stream: `events:submissions`) — Payload: `{ student_id, exercise_id, submission_id, status, test_results, attempt_number, timestamp }`
  - `code.snapshot.captured` (stream: `events:code`) — Payload: `{ student_id, exercise_id, submission_id, code, snapshot_at }`

### Consume
- SandboxService (de EPIC-07)
- Ejercicios (de EPIC-06)
- Auth (de EPIC-03)

### Modelos (owner — schema: operational)
- `submissions`: id (UUID PK), student_id (FK → users), exercise_id (FK → exercises), code (TEXT), status (ENUM: pending/running/passed/failed/error), score (NUMERIC 5,2, nullable) -- Tasa de aprobación de test cases automatizados (0-100%). NO es la evaluación pedagógica. La evaluación real es E = f(N1,N2,N3,N4,Qe) en cognitive_metrics., feedback (TEXT, nullable), test_results (JSONB, nullable), stdout (TEXT, nullable), stderr (TEXT, nullable), attempt_number (SMALLINT, default 1), submitted_at (TIMESTAMPTZ), evaluated_at (TIMESTAMPTZ, nullable)
- `code_snapshots`: id (UUID PK), student_id (UUID), exercise_id (UUID), submission_id (FK nullable → submissions), code (TEXT), snapshot_at (TIMESTAMPTZ)

**IMPORTANTE**: `code_snapshots` son INMUTABLES. No hay endpoint de UPDATE ni DELETE. Son evidencia de proceso cognitivo.

## Dependencias
- **Blocked by**: EPIC-06, EPIC-07 (necesita ejercicios y sandbox)
- **Blocks**: EPIC-09 (el chat del tutor necesita contexto del código actual), EPIC-13 (CTR consume eventos de submissions), EPIC-16 (traza visual consume code_snapshots)

## Stories

- [ ] Modelos SQLAlchemy: submissions (sin campo draft, con attempt_number, evaluated_at, feedback), code_snapshots (sin edit_distance) + migración Alembic
- [ ] SubmissionService: crear submission, ejecutar (usa sandbox), submit final con attempt_number
- [ ] SnapshotService: guardar snapshot (inmutable)
- [ ] Endpoints REST: submissions CRUD + snapshots
- [ ] Frontend: integración Monaco Editor (syntax highlighting, auto-save)
- [ ] Frontend: auto-snapshot cada 30s + ante ejecución
- [ ] Frontend: botón "Enviar Solución" con confirmación
- [ ] Frontend: historial de submissions del alumno
- [ ] Frontend docente: ver submissions de su comisión
- [ ] Producir eventos `exercise.submitted` y `code.snapshot.captured` para Event Bus
- [ ] Tests de integración: flujo completo pending→running→passed/failed, snapshots, RBAC, nombres de eventos correctos

## Criterio de Done

- Alumno puede escribir código en Monaco, ejecutar, ver resultados, e iterar
- Snapshots se guardan automáticamente (30s + ante ejecución)
- Alumno puede enviar submission final
- Status inicial de submissions es `pending` (no `draft`)
- Docente puede ver submissions de su comisión
- Eventos `exercise.submitted` y `code.snapshot.captured` se emiten al Event Bus con nombres correctos
- Code snapshots son inmutables (no hay UPDATE/DELETE)
- Tests de integración pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/01-negocio/05_flujos_principales.md`
