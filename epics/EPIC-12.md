# EPIC-12: Reflexión Post-Ejercicio

> **Issue**: #12 | **Milestone**: Fase 2 — Tutor IA | **Labels**: epic, fase-2, priority:high

## Contexto

Después de enviar una submission, el alumno completa un formulario de reflexión guiado. Esto captura metacognición explícita: qué fue difícil, qué estrategia usó, cómo evaluó su uso de la IA, qué haría diferente. La reflexión se persiste en schema `operational` (owner: Fase 2) y se emite como evento para que Fase 3 lo incorpore al CTR.

**Decisión de diseño**: La reflexión se persiste en una tabla separada `reflections`, NO como campo en `submissions`. Razones: (1) mantiene `submissions` limpia y enfocada en el producto de código, (2) las reflexiones son independientemente queryables para análisis cognitivo, (3) son opcionales en tiempo (el alumno puede reflexionar después de hacer submit). Esta tabla es una extensión de Fase 2 al schema `operational` — **no está en el modelo de datos original del KB**, fue diseñada durante la planificación de EPICs como tabla explícita.

## Alcance

### Backend
- Modelo SQLAlchemy: tabla `reflections` (nueva, extensión Fase 2 al schema operational)
- Domain service: `ReflectionService`
- Endpoints:
  - `POST /api/v1/submissions/{id}/reflection` — alumno envía reflexión
  - `GET /api/v1/submissions/{id}/reflection` — ver reflexión (alumno propia, docente de su comisión)
- Validación: reflexión solo se puede enviar después de submit (submission debe existir y pertenecer al alumno)
- Validación: solo una reflexión por submission (UNIQUE constraint en submission_id)
- Schema de reflexión (campos guiados, todos requeridos):
  - `difficulty_perception` (INT 1-5)
  - `strategy_description` (TEXT)
  - `ai_usage_evaluation` (TEXT)
  - `what_would_change` (TEXT)
  - `confidence_level` (INT 1-5)

### Frontend
- Panel de reflexión que aparece DESPUÉS de enviar una submission
- Formulario guiado con los campos de reflexión
- Validación client-side (todos los campos requeridos)
- Confirmación de envío
- Vista de reflexión enviada (read-only)
- Docente: ver reflexiones de alumnos de su comisión

## Contratos

### Produce
- Endpoints REST de reflexión
- Tabla `reflections` en schema `operational`
- Evento: `reflection.submitted` (stream: `events:submissions`, student_id, exercise_id, submission_id, difficulty_perception, confidence_level, timestamp)

  **Nota**: `reflection.submitted` es un nuevo tipo de evento definido en Fase 2. No está en el KB original. Fase 3 debe registrar un consumer para este evento en su Event Bus subscription al armar el CTR. Se publica en `events:submissions` porque las reflexiones pertenecen al dominio operacional de submissions.

### Consume
- Submissions (de EPIC-08) — reflexión se asocia a una submission
- Auth (de EPIC-03)

### Modelos (owner — schema: operational)
- `operational.reflections`: id (UUID PK), submission_id (FK → submissions, UNIQUE), student_id (FK → users), difficulty_perception (INT CHECK (difficulty_perception BETWEEN 1 AND 5)), strategy_description (TEXT), ai_usage_evaluation (TEXT), what_would_change (TEXT), confidence_level (INT CHECK (confidence_level BETWEEN 1 AND 5)), created_at (TIMESTAMPTZ)

  **Nota**: Esta tabla es una extensión de Fase 2 al schema `operational`. No estaba en el modelo de datos original del KB — fue diseñada durante la planificación de EPICs como tabla separada para mantener submissions limpio y reflexiones independientemente queryables. Fase 3 consume esta tabla via REST, nunca con queries directos.

## Dependencias
- **Blocked by**: EPIC-03 (auth protege los endpoints de reflexión), EPIC-08 (necesita submissions)
- **Blocks**: EPIC-13 (CTR incorpora reflexión como evento cognitivo via `reflection.submitted`)

## Stories

- [ ] Modelo SQLAlchemy: reflections + migración Alembic
- [ ] ReflectionService con validación (solo post-submit, una por submission, RBAC)
- [ ] Endpoints REST: crear y ver reflexión
- [ ] Frontend: panel de reflexión post-submission (formulario guiado)
- [ ] Frontend: validación client-side (todos los campos requeridos)
- [ ] Frontend: vista read-only de reflexión enviada
- [ ] Frontend docente: ver reflexiones de su comisión
- [ ] Producir evento `reflection.submitted` para Event Bus
- [ ] Tests: flujo completo, validaciones, RBAC

## Criterio de Done

- Alumno puede completar reflexión después de enviar submission
- Solo una reflexión por submission (constraint y validación)
- Docente puede ver reflexiones de su comisión
- Evento `reflection.submitted` emitido para Fase 3
- La tabla `reflections` existe en schema `operational` como extensión explícita de Fase 2
- Tests pasan

## Referencia
- `knowledge-base/01-negocio/05_flujos_principales.md`
- `knowledge-base/01-negocio/04_reglas_de_negocio.md`
