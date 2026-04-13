# EPIC-14: Métricas Cognitivas y Evaluation Engine

> **Issue**: #14 | **Milestone**: Fase 3 — Motor Cognitivo | **Labels**: epic, fase-3, priority:critical

**Nivel de gobernanza**: CRITICAL — cambios requieren revisión formal

## Contexto

El motor que transforma el CTR en métricas útiles. Calcula scores N1-N4 por sesión, calidad epistémica (Qe), dependency score, y la función evaluativa formal: E = f(N1, N2, N3, N4, Qe). Esto es lo que el docente ve en el dashboard — no una nota de "correcto/incorrecto" sino un perfil cognitivo multidimensional.

## Alcance

### Backend
- Modelos SQLAlchemy: `cognitive_metrics`, `reasoning_records`
- **Cognitive Worker**: calcula métricas por sesión cognitiva cerrada
  - Scores N1-N4 (NUMERIC 0-100, tipo NUMERIC(5,2)) basados en rúbrica N4 (Anexo B)
  - Help-seeking ratio (NUMERIC(4,3), 0.000 a 1.000)
  - Autonomy index (NUMERIC(4,3), 0.000 a 1.000)
  - Risk level (low/medium/high/critical) derivado de las métricas
- **Evaluation Engine**: `E = f(N1, N2, N3, N4, Qe)`
  - Fórmula configurable (pesos por componente)
  - No es un número final — es un PERFIL multidimensional
  - El resultado se almacena como JSONB en `cognitive_sessions.n4_final_score` al cierre de sesión, NO en cognitive_metrics
- **Agregados por comisión**: `cognitive_sessions` incluye `commission_id` (denormalizado al crear la sesión desde el payload del evento o via REST a Fase 1). Las queries de agregación usan `cognitive_sessions.commission_id` directamente, sin JOINs cross-schema.

> **Nota**: El `commission_id` se obtiene al crear la sesión: el payload de `reads_problem` (EPIC-06) ya incluye `commission_id`. EPIC-13 lo almacena en `cognitive_sessions.commission_id` en ese momento. Si el payload no lo incluye, EPIC-13 lo resuelve via REST a `GET /api/v1/exercises/{id}` antes de persistir la sesión.

- Endpoints:
  - `GET /api/v1/cognitive/sessions/{id}/metrics` — métricas de una sesión
  - `GET /api/v1/teacher/courses/{id}/dashboard` — agregados por comisión (usa `commission_id` denormalizado)
  - `GET /api/v1/teacher/students/{id}/profile` — perfil cognitivo individual
  - `GET /api/v1/student/me/progress` — alumno ve su progreso

### Frontend
- **Dashboard docente**:
  - Vista de comisión: promedios N1-N4, distribución Qe, indicadores clave
  - Radar chart N1-N4 por alumno (Recharts)
  - Tabla de alumnos con scores multidimensionales
  - Filtros: por ejercicio, por período, por nivel de riesgo
- **Dashboard alumno**:
  - Progreso cognitivo en el tiempo (gráfico de evolución)
  - Scores agregados (sin detalle que permita gaming)

## Contratos

### Produce
- Modelos `cognitive_metrics`, `reasoning_records` en schema `cognitive`
- Endpoints de métricas y dashboard
- Datos para EPIC-15 (risk detection consume métricas)
- Datos para EPIC-16 (traza visual incluye métricas)

### Consume
- Sesiones cognitivas con CTR (de EPIC-13) — triggerado al cerrar sesión (status = closed)
- Rúbrica N4 (`rubrics/n4_anexo_b.yaml`)
- Cursos y comisiones (de EPIC-05) — `commission_id` ya está denormalizado en `cognitive_sessions` (ver nota arriba); no se requiere JOIN cross-schema en tiempo de query

### Modelos (owner — schema: cognitive)

**cognitive_metrics**
- `id` (UUID PK)
- `session_id` (UUID FK → cognitive_sessions.id, UNIQUE)
- `n1_comprehension_score` (NUMERIC(5,2), NULLABLE) — Score 0-100
- `n2_strategy_score` (NUMERIC(5,2), NULLABLE) — Score 0-100
- `n3_validation_score` (NUMERIC(5,2), NULLABLE) — Score 0-100
- `n4_ai_interaction_score` (NUMERIC(5,2), NULLABLE) — Score 0-100
- `total_interactions` (INTEGER, NOT NULL, DEFAULT 0)
- `help_seeking_ratio` (NUMERIC(4,3), NULLABLE) — 0.000 a 1.000
- `autonomy_index` (NUMERIC(4,3), NULLABLE) — 0.000 a 1.000
- `risk_level` (ENUM: low/medium/high/critical, NULLABLE)
- `computed_at` (TIMESTAMPTZ, NULLABLE)

Nota: tipos son NUMERIC, no FLOAT. `evaluation_result` y `epistemic_quality` NO están en este modelo — la función E = f(N1,N2,N3,N4,Qe) se almacena en `cognitive_sessions.n4_final_score`.

**reasoning_records** (INMUTABLE — sin UPDATE ni DELETE, son evidencia)
- `id` (UUID PK)
- `session_id` (UUID FK → cognitive_sessions.id, NOT NULL)
- `record_type` (ENUM: hypothesis/strategy/validation/reflection, NOT NULL)
- `details` (JSONB, NOT NULL)
- `previous_hash` (VARCHAR 64, NOT NULL) — hash chain
- `current_hash` (VARCHAR 64, NOT NULL) — SHA-256 de este registro
- `created_at` (TIMESTAMPTZ, NOT NULL)

## Dependencias
- **Blocked by**: EPIC-13 (necesita CTR construido)
- **Blocks**: EPIC-15 (risk detection consume métricas), EPIC-16 (traza visual consume métricas cognitivas)

## Stories

- [ ] Modelos SQLAlchemy: cognitive_metrics, reasoning_records + migración
- [ ] Cognitive Worker: calcular N1-N4 scores (NUMERIC 0-100) basados en rúbrica
- [ ] Cognitive Worker: help_seeking_ratio, autonomy_index (NUMERIC 0.000-1.000), risk_level
- [ ] Evaluation Engine: E = f(N1, N2, N3, N4, Qe) con pesos configurables — resultado JSONB en cognitive_sessions.n4_final_score
- [ ] reasoning_records: inmutabilidad con hash chain (previous_hash → current_hash)
- [ ] Endpoints: métricas por sesión, dashboard docente, perfil alumno, progreso alumno
- [ ] Queries de agregación por comisión usando `cognitive_sessions.commission_id` (campo denormalizado — no JOIN cross-schema)
- [ ] Frontend docente: dashboard de comisión (promedios, distribución, filtros)
- [ ] Frontend docente: radar chart N1-N4 por alumno (Recharts)
- [ ] Frontend docente: tabla de alumnos con scores
- [ ] Frontend alumno: vista de progreso cognitivo
- [ ] Tests: scoring contra rúbrica conocida (resultados deterministas)
- [ ] Tests: Qe con edge cases (sesión sin CTR, sesión corta)
- [ ] Tests: agregación por comisión usando `commission_id` denormalizado (sin cross-schema JOIN)

## Criterio de Done

- Métricas se calculan automáticamente al cerrar una sesión cognitiva
- Dashboard docente muestra agregados por comisión con radar chart
- Queries de comisión usan `cognitive_sessions.commission_id` (denormalizado) — sin JOINs cross-schema
- Alumno puede ver su progreso
- Evaluación es multidimensional (perfil, no número)
- Tests con resultados deterministas pasan

## Referencia
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `rubrics/n4_anexo_b.yaml`
- Documento maestro: función evaluativa E = f(N1, N2, N3, N4, Qe)
