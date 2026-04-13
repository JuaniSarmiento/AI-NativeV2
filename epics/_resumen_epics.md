# Resumen Consolidado — EPICs

> 19 EPICs leídas. Fuente de verdad: knowledge-base (post-auditoría 2026-04-13).
> Última actualización: 2026-04-13

---

## EPIC-01: Infraestructura y DevOps (Fase 0)
**Alcance**: Monorepo, Docker Compose, CI/CD, pre-commit, Event Bus (4 Redis Streams), event_outbox.
**Issues vs KB**: Ninguno ✅

## EPIC-02: Base de Datos y Schemas (Fase 0)
**Alcance**: SQLAlchemy async, 4 schemas PostgreSQL, Alembic multi-schema, UoW, BaseRepository, users+courses+commissions+event_outbox.
**Modelos**: users, courses, commissions, event_outbox — alineados con KB ✅
**Issues vs KB**: Ninguno ✅

## EPIC-03: Autenticación JWT y RBAC (Fase 0)
**Alcance**: Auth JWT (15min/7d), refresh rotation, bcrypt, RBAC 3 roles, rate limiting, frontend login/registro.
**Issues vs KB**:
- Redis key `token:blacklist:{jti}` — KB usa `auth:blacklist:{jti}`. **FIX NECESARIO**.

## EPIC-04: Contratos OpenAPI, MSW y Design System (Fase 0)
**Alcance**: OpenAPI spec, MSW, Design System TailwindCSS 4, App Shell, React Router.
**Issues vs KB**:
- Healthcheck `GET /health` — debería ser `GET /api/v1/health`. **FIX NECESARIO**.

## EPIC-05: Gestión de Cursos y Comisiones (Fase 1)
**Alcance**: CRUD courses, commissions, enrollments. Frontend docente ABM + alumno inscripción.
**Issues vs KB**:
- Dependencia dice "EPIC-06 (ejercicios pertenecen a comisiones)" — debería decir "ejercicios pertenecen a CURSOS". **FIX NECESARIO**.

## EPIC-06: Gestión de Ejercicios (Fase 1)
**Alcance**: CRUD exercises, filtros, evento reads_problem, frontend ABM docente + listado alumno.
**Issues vs KB** (CRÍTICOS):
- `exercises.commission_id` — debería ser `course_id (FK → courses)`. **FIX NECESARIO**.
- Endpoint `GET/POST /api/v1/commissions/{id}/exercises` — debería ser `/courses/{id}/exercises`. **FIX NECESARIO**.
- Dice "ejercicios pertenecen a comisiones, NO a cursos" — contradice decisión de KB. **FIX NECESARIO**.
- reads_problem va por `events:submissions` pero conceptualmente es de la fase de exercises. Técnicamente OK (el stream agrupa eventos operacionales).

## EPIC-07: Sandbox de Ejecución Segura (Fase 1)
**Alcance**: Subprocess con límites, test runner, panel output frontend.
**Issues vs KB**:
- Endpoint `POST /api/v1/exercises/{id}/run` — KB canónico es `POST /api/v1/student/exercises/{id}/run`. **FIX NECESARIO**.

## EPIC-08: Submission Flow y Code Snapshots (Fase 1)
**Alcance**: Submissions, code snapshots inmutables, Monaco Editor, eventos exercise.submitted + code.snapshot.captured.
**Issues vs KB**: Ninguno significativo ✅

## EPIC-09: Chat Streaming con Tutor IA (Fase 2)
**Alcance**: WebSocket /ws/tutor/chat, Anthropic adapter, rate limiting, tutor_interactions + tutor_system_prompts.
**Issues vs KB**:
- Dice `tutor_interactions NO tiene session_id` — KB dice que SÍ tiene session_id (correlación lógica). **FIX NECESARIO**.
- Modelo tutor_interactions falta `session_id` en la definición. **FIX NECESARIO**.

## EPIC-10: Prompt Engine y Guardrails (Fase 2)
**Alcance**: ContextBuilder, GuardrailsProcessor, system prompt socrático v1, governance_events por violaciones.
**Issues vs KB**: Ninguno ✅

## EPIC-11: Clasificación N4 y Governance Events (Fase 2)
**Alcance**: Clasificador N4 por interacción, governance_events modelo, endpoint admin.
**Issues vs KB**: Ninguno ✅. Modelo governance_events alineado con KB.

## EPIC-12: Reflexión Post-Ejercicio (Fase 2)
**Alcance**: Tabla reflections, endpoints reflexión, evento reflection.submitted.
**Issues vs KB**:
- Dice "tabla no estaba en el modelo original del KB" — ya la agregamos. Nota obsoleta. **FIX NECESARIO** (remover nota).

## EPIC-13: Event Classifier y CTR Builder (Fase 3)
**Alcance**: cognitive_sessions, cognitive_events, Event Bus consumer, hash chain, clasificación N4.
**Issues vs KB**:
- cognitive_sessions tiene `commission_id` denormalizado — NO está en KB modelo canónico. **DECISIÓN**: agregar a KB (es un campo útil para evitar cross-schema joins).

## EPIC-14: Métricas Cognitivas y Evaluation Engine (Fase 3)
**Alcance**: cognitive_metrics, reasoning_records, Cognitive Worker, Evaluation Engine, dashboard docente.
**Issues vs KB**:
- `reasoning_records` usa `current_hash` — debería ser `event_hash`. **FIX NECESARIO**.
- `cognitive_metrics` le faltan campos Qe (qe_score, qe_quality_prompt, etc.). **FIX NECESARIO**.

## EPIC-15: Risk Detection (Fase 3)
**Alcance**: risk_assessments, Risk Worker, alertas docente, acknowledge.
**Issues vs KB**: Ninguno ✅. commission_id correcto, risk_factors JSONB alineado.

## EPIC-16: Traza Cognitiva Visual (Fase 3)
**Alcance**: Timeline color-coded, code evolution diffs, chat integrado, governance reports, hash chain verification.
**Issues vs KB**: Ninguno ✅. Acceso cross-schema via REST.

## EPIC-17: Remover MSW y Conectar APIs Reales (Integración)
**Issues vs KB**: Ninguno ✅

## EPIC-18: Testing E2E con Playwright (Integración)
**Issues vs KB**: Ninguno ✅

## EPIC-19: Deploy Staging y Piloto (Integración)
**Issues vs KB**: Ninguno ✅

---

## RESUMEN DE INCONSISTENCIAS EPIC vs KB

| EPIC | Issue | Estado |
|------|-------|--------|
| 03 | Redis key `token:blacklist:{jti}` → `auth:blacklist:{jti}` | RESUELTO ✅ |
| 04 | Healthcheck `/health` → `/api/v1/health` | RESUELTO ✅ |
| 05 | "ejercicios pertenecen a comisiones" → "a cursos" | RESUELTO ✅ |
| 06 | `commission_id` → `course_id`, endpoints `/commissions/` → `/courses/` | RESUELTO ✅ |
| 07 | Endpoint sin `/student/` prefix | RESUELTO ✅ |
| 09 | tutor_interactions falta `session_id` | RESUELTO ✅ |
| 12 | Nota obsoleta sobre tabla reflections | RESUELTO ✅ |
| 14 | `current_hash` → `event_hash`, faltan campos Qe | RESUELTO ✅ |
| 13 | cognitive_sessions.commission_id → agregado a KB | RESUELTO ✅ |

---

## INCONSISTENCIAS ENTRE EPICs

| EPICs | Issue |
|-------|-------|
| 05 vs 06 | EPIC-05 dice exercises pertenecen a comisiones, EPIC-06 refuerza eso. Ambos mal. |
| 09 vs KB | EPIC-09 niega session_id en tutor_interactions, KB lo tiene. |
| 13 vs 14 | EPIC-13 define cognitive_sessions sin campos Qe, EPIC-14 define cognitive_metrics sin Qe. Ambos incompletos vs KB. |
| 06 vs 07 | EPIC-06 usa `/commissions/{id}/exercises`, EPIC-07 usa `/exercises/{id}/run` (sin `/student/` prefix). Rutas inconsistentes entre sí y con KB. |
