## Why

EPIC-13 construyó el CTR (Cognitive Trace Record) — la cadena inmutable de eventos cognitivos por sesión. Pero el CTR es datos crudos: sin interpretación, sin métricas, sin valor para el docente. EPIC-14 transforma ese registro en métricas accionables: scores N1-N4, calidad epistémica (Qe), dependency score, y la función evaluativa formal `E = f(N1, N2, N3, N4, Qe)`. Es lo que habilita que el docente vea un perfil cognitivo multidimensional en lugar de "aprobó/desaprobó", y que el alumno entienda su proceso de aprendizaje.

## What Changes

- **Nuevos modelos** en schema `cognitive`: `cognitive_metrics` (1:1 con sesión) y `reasoning_records` (inmutable, hash-chained)
- **Cognitive Worker**: servicio que al cerrar una sesión calcula N1-N4 scores (NUMERIC 0-100), help-seeking ratio, autonomy index, dependency score, reflection score, y risk level
- **Evaluation Engine**: aplica `E = f(N1, N2, N3, N4, Qe)` con pesos configurables, almacena resultado JSONB en `cognitive_sessions.n4_final_score`
- **Rúbrica N4**: archivo `rubrics/n4_anexo_b.yaml` con criterios de scoring por nivel
- **4 endpoints REST**: métricas por sesión, dashboard docente por comisión, perfil cognitivo de alumno, progreso del alumno
- **Frontend docente**: dashboard con radar chart N1-N4 (Recharts), tabla de alumnos, filtros por ejercicio/período/riesgo
- **Frontend alumno**: vista de progreso cognitivo agregado (sin detalle que permita gaming)

## Capabilities

### New Capabilities
- `cognitive-metrics-model`: Modelos SQLAlchemy para `cognitive_metrics` y `reasoning_records` en schema cognitive + migración Alembic
- `cognitive-worker`: Worker que calcula métricas N1-N4, Qe, ratios y risk level al cierre de sesión cognitiva
- `evaluation-engine`: Función evaluativa `E = f(N1, N2, N3, N4, Qe)` con pesos configurables, resultado JSONB
- `cognitive-metrics-api`: Endpoints REST para métricas por sesión, dashboard docente, perfil alumno, progreso alumno
- `teacher-dashboard-frontend`: Dashboard docente con radar chart N1-N4, tabla de alumnos, agregados por comisión
- `student-progress-frontend`: Vista de progreso cognitivo del alumno

### Modified Capabilities
_(ninguna — esta EPIC agrega capacidades nuevas sin modificar specs existentes)_

## Impact

- **Schema cognitive**: 2 tablas nuevas (`cognitive_metrics`, `reasoning_records`), 1 migración Alembic
- **cognitive_sessions.n4_final_score**: campo JSONB existente que se empieza a poblar
- **Backend features**: nuevo módulo `evaluation/` + extensión de `cognitive/` con worker y repos
- **Frontend**: nuevas páginas de dashboard docente y progreso alumno
- **Dependencia nueva**: Recharts para radar chart en frontend
- **Downstream**: EPIC-15 (risk detection) y EPIC-16 (traza visual) consumen las métricas producidas aquí
