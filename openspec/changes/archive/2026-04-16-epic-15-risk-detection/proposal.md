## Why

El sistema calcula metricas cognitivas por sesion (EPIC-14) pero no agrega esa informacion a nivel alumno/comision para detectar patrones de riesgo sostenidos. Un alumno puede tener varias sesiones con dependency_score alto sin que el docente se entere hasta que es tarde. EPIC-15 introduce un sistema de alerta temprana que analiza patrones acumulados y notifica al docente, quien puede marcar alertas como revisadas (acknowledge).

## What Changes

- Nuevo modelo `risk_assessments` en schema `analytics` con `commission_id` (no course_id), `risk_factors` JSONB, `triggered_by` (automatic/manual/threshold), y campos de acknowledge (`acknowledged_by`, `acknowledged_at`)
- Risk Worker que analiza CognitiveMetrics acumuladas por alumno/comision y detecta factores de riesgo (dependency, disengagement, stagnation) almacenados en `risk_factors` JSONB
- Calculo de `risk_level` (low/medium/high/critical) y generacion de `recommendation` textual para el docente
- 3 endpoints REST para docentes: riesgos por comision, historial por alumno, acknowledge de alerta
- Tabla de alumnos en riesgo en el dashboard docente con color-coding, factores JSONB expandidos, boton acknowledge
- Badges de riesgo en la tabla general de alumnos del dashboard existente

## Capabilities

### New Capabilities
- `risk-assessment-model`: Modelo SQLAlchemy `risk_assessments` en schema analytics, migracion Alembic, y repository
- `risk-worker`: Worker que detecta factores de riesgo por alumno/comision, calcula risk_level, genera recommendations
- `risk-api`: Endpoints REST para docentes — listar riesgos por comision, historial por alumno, acknowledge
- `risk-dashboard-frontend`: Tabla de alumnos en riesgo con color-coding, factores, acknowledge, badges en tabla existente

### Modified Capabilities
- `teacher-dashboard-frontend`: Se agrega seccion de alertas de riesgo y badges de riesgo en la tabla de alumnos existente

## Impact

- **Backend**: Nuevo feature module `app/features/risk/` con models, repositories, service (worker), schemas, router. Nueva migracion Alembic para `analytics.risk_assessments`
- **Frontend**: Nuevos componentes en `features/teacher/dashboard/` — RiskAlertsTable, RiskBadge. Modificacion de StudentScoresTable para badges
- **API**: 3 nuevos endpoints bajo `/api/v1/teacher/`
- **DB**: Nueva tabla en schema `analytics`. Sin cross-schema FK (usa UUIDs denormalizados como cognitive_sessions)
- **Dependencias**: Consume `cognitive.cognitive_metrics` via repo (mismo patron que evaluation router). Consume `operational.enrollments` para listar alumnos de la comision
