## Context

EPIC-14 implemento el MetricsEngine que calcula scores N1-N4, Qe, dependency_score y risk_level por sesion cognitiva individual. Sin embargo, no hay agregacion a nivel alumno/comision para detectar patrones sostenidos. Un alumno puede acumular 5 sesiones con dependency_score > 0.7 sin que el docente se entere.

El modelo de datos ya tiene `cognitive.cognitive_metrics` con risk_level per-session. Lo que falta es un worker que agregue esos datos y produzca risk assessments persistentes en el schema `analytics`, mas endpoints para que el docente los consulte y haga acknowledge.

El teacher dashboard (EPIC-14) ya existe en `frontend/src/features/teacher/dashboard/` con radar chart, tabla de alumnos y distribution card. EPIC-15 agrega una tabla de alertas de riesgo y badges.

## Goals / Non-Goals

**Goals:**
- Detectar automaticamente alumnos en riesgo por comision basado en metricas cognitivas acumuladas
- Permitir al docente ver, filtrar y hacer acknowledge de alertas de riesgo
- Factores de riesgo codificados en JSONB (dependency, disengagement, stagnation) — extensible sin migraciones
- Job idempotente: ejecutar dos veces no duplica assessments
- Soporte para triggered_by: automatic (post-sesion), manual (docente), threshold (umbral)

**Non-Goals:**
- Notificaciones push o email al docente (EPIC futura)
- Machine learning o modelos predictivos — la deteccion es rule-based con umbrales configurables
- Risk assessment a nivel curso (solo comision)
- Dashboard de riesgo para admin (reutiliza endpoints de docente con RBAC)

## Decisions

### D1: Modelo en schema `analytics` sin FK cross-schema

El modelo `risk_assessments` vive en el schema `analytics` con `student_id` y `commission_id` como UUIDs sin FK, igual que `cognitive_sessions`. Esto mantiene el patron de ownership por fase.

**Alternativa descartada**: FK a `operational.users` y `operational.commissions` — viola la regla de ownership por schema.

### D2: risk_factors como JSONB, no como enum top-level

Los factores de riesgo (dependency, disengagement, stagnation, etc.) se almacenan dentro de `risk_factors` JSONB, no como un campo enum separado. Esto permite agregar nuevos factores sin migracion.

Estructura del JSONB:
```json
{
  "dependency": { "score": 0.75, "sessions_above_threshold": 4, "threshold": 0.5 },
  "disengagement": { "score": 0.3, "sessions_without_activity": 2 },
  "stagnation": { "score": 0.6, "n1_trend": "declining", "sessions_analyzed": 5 }
}
```

### D3: Feature module `app/features/risk/` separado

Nuevo modulo en features/ con models, repositories, service, schemas, router. No se mezcla con evaluation/ porque risk assessment es un dominio diferente (alertas operativas vs metricas cognitivas).

### D4: RiskWorker como servicio sincrono invocable, no como consumer async

A diferencia del CognitiveEventConsumer que corre continuamente escuchando Redis Streams, el RiskWorker es un servicio que se invoca:
1. **Post-session close**: cuando el MetricsEngine termina de computar metrics, llama al RiskWorker
2. **Manual**: endpoint para que el docente trigger un recalculo
3. **Threshold**: potencial cron job futuro

Esto simplifica el diseno — no necesita otro consumer de Redis Streams.

**Alternativa descartada**: Consumer en Redis Streams — over-engineering para un calculo que corre pocas veces al dia.

### D5: Idempotencia via UPSERT por (student_id, commission_id, assessed_at::date)

Para evitar duplicados, el worker hace un upsert: si ya existe un assessment para el mismo alumno, comision y dia, lo actualiza en vez de crear uno nuevo. Esto permite re-ejecutar el worker sin efectos secundarios.

### D6: Frontend integrado en el dashboard existente

Los componentes de riesgo se agregan al TeacherDashboard existente, no como pagina separada. La tabla de riesgo aparece debajo del radar chart y la tabla de alumnos. Se agrega un badge de riesgo a la tabla StudentScoresTable existente.

## Risks / Trade-offs

- **[Performance]** Agregar multiples sesiones por alumno puede ser lento con muchos alumnos. → Mitigation: queries con limites razonables, indices en cognitive_metrics.session_id y cognitive_sessions.commission_id ya existen.
- **[Stale data]** Los risk assessments son snapshots — pueden quedar desactualizados si el alumno mejora. → Mitigation: assessed_at timestamp claro, recalculo automatico post-sesion.
- **[Factor drift]** Nuevos factores de riesgo requieren cambios en el worker pero no en el schema. → Mitigation: JSONB extensible, el frontend renderiza dinamicamente los factores presentes.
- **[Cross-schema reads]** El worker lee de `cognitive.cognitive_metrics` y `cognitive.cognitive_sessions`. → Mitigation: lectura via repositorios existentes (CognitiveMetricsRepository), no queries ad-hoc.
