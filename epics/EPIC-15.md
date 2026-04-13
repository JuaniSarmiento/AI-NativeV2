# EPIC-15: Risk Detection

> **Issue**: #15 | **Milestone**: Fase 3 — Motor Cognitivo | **Labels**: epic, fase-3, priority:high

## Contexto

Detecta alumnos en riesgo analizando patrones a nivel alumno/comisión. Los factores de riesgo (dependency, disengagement, stagnation, etc.) se codifican DENTRO del campo `risk_factors` (JSONB), no como un enum de nivel superior. Es una ALERTA TEMPRANA para el docente — puede intervenir antes de que sea tarde. El docente puede marcar una alerta como revisada ("acknowledge").

## Alcance

### Backend
- Modelo SQLAlchemy: `risk_assessments`
- **Risk Worker**: analiza patrones por alumno por comisión
  - Los factores de riesgo (dependency, disengagement, stagnation, etc.) se almacenan en `risk_factors` (JSONB) — no como enum top-level
  - Niveles de riesgo: low / medium / high / critical
  - Triggers: automático (post-sesión), manual (docente), o por umbral (threshold)
- Endpoint:
  - `GET /api/v1/teacher/commissions/{id}/risks` — alumnos en riesgo por comisión
  - `GET /api/v1/teacher/students/{id}/risks` — historial de riesgo de un alumno
  - `PATCH /api/v1/teacher/risks/{id}/acknowledge` — docente marca la alerta como revisada
- Job periódico (o trigger post-sesión) para recalcular riesgo

### Frontend
- **Tabla de alumnos en riesgo** en el dashboard docente:
  - Color-coded por risk_level (verde/amarillo/naranja/rojo)
  - Factores de riesgo derivados del JSONB `risk_factors`
  - Botón "Acknowledge" para marcar como revisada (muestra acknowledged_by + acknowledged_at)
  - Click → perfil del alumno (EPIC-14)
- Badges/indicadores de riesgo en la tabla general de alumnos

## Contratos

### Produce
- Modelo `risk_assessments` en schema `analytics`
- Endpoints de riesgo por comisión y por alumno
- Datos para dashboard docente (EPIC-14 ya tiene el dashboard, esta EPIC agrega la tabla de riesgo)

### Consume
- Métricas cognitivas (de EPIC-14)
- Sesiones cognitivas (de EPIC-13)
- Enrollments por comisión (de EPIC-05)

### Modelos (owner — schema: analytics)

**risk_assessments**
- `id` (UUID PK)
- `student_id` (UUID, NOT NULL)
- `commission_id` (UUID, NOT NULL) — NOT course_id; los riesgos son por comisión
- `risk_level` (ENUM: low/medium/high/critical, NOT NULL)
- `risk_factors` (JSONB, NOT NULL) — factores que contribuyeron al riesgo (dependency, disengagement, stagnation, etc. codificados aquí)
- `recommendation` (TEXT, NULLABLE) — recomendación generada para el docente
- `triggered_by` (ENUM: automatic/manual/threshold, NOT NULL)
- `assessed_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- `acknowledged_by` (UUID, NULLABLE) — docente que revisó la alerta
- `acknowledged_at` (TIMESTAMPTZ, NULLABLE) — cuándo fue revisada

## Dependencias
- **Blocked by**: EPIC-14 (necesita métricas cognitivas calculadas)
- **Blocks**: EPIC-17 (dashboard docente consume alertas de riesgo)

## Stories

- [ ] Modelo SQLAlchemy: risk_assessments + migración Alembic (commission_id, risk_factors JSONB, triggered_by, acknowledged_by/at)
- [ ] Risk Worker: detección de factores de riesgo (dependency, disengagement, stagnation) almacenados en risk_factors JSONB
- [ ] Risk Worker: cálculo de risk_level (low/medium/high/critical) y recommendation
- [ ] Risk Worker: soporte para triggered_by (automatic/manual/threshold)
- [ ] Endpoint acknowledge: PATCH /api/v1/teacher/risks/{id}/acknowledge — docente marca como revisada
- [ ] Endpoints: riesgos por comisión, historial por alumno
- [ ] Frontend: tabla de alumnos en riesgo (color-coded, factores JSONB, botón Acknowledge, acknowledged_by/at)
- [ ] Frontend: badges de riesgo en tabla general de alumnos
- [ ] Tests: detección correcta de factores de riesgo en risk_factors JSONB
- [ ] Tests: idempotencia del job (correr dos veces no duplica)
- [ ] Tests: flujo acknowledge (set/unset acknowledged_by)

## Criterio de Done

- Alumnos en riesgo se detectan automáticamente por comisión (commission_id, no course_id)
- Docente ve tabla de riesgo con color-coding y factores JSONB
- Docente puede hacer acknowledge de una alerta (acknowledged_by + acknowledged_at)
- Factores de riesgo (dependency/disengagement/stagnation) codificados en risk_factors JSONB
- triggered_by refleja el origen correcto (automatic/manual/threshold)
- Job es idempotente
- Tests pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `knowledge-base/01-negocio/04_reglas_de_negocio.md`
