## Context

EPIC-13 construyó el CTR: sesiones cognitivas con eventos inmutables hash-chained. Al cerrar una sesión (por `submission.created`, `session.closed`, o timeout 30min), `CognitiveService.close_session()` sella la cadena con `session_hash`. Pero hoy no pasa nada después del cierre — los datos quedan sin interpretar.

El campo `cognitive_sessions.n4_final_score` (JSONB, nullable) ya existe en el modelo pero nunca se pobla. EPIC-14 es el motor que transforma eventos crudos en métricas accionables.

**Estado actual del consumer**: `CognitiveEventConsumer._process_event()` llama `service.close_session()` en la misma transacción del último evento. El timeout checker corre cada 5 minutos cerrando sesiones stale. Ambos son puntos de trigger para el cálculo de métricas.

## Goals / Non-Goals

**Goals:**
- Calcular métricas N1-N4, Qe, ratios y risk level automáticamente al cerrar una sesión cognitiva
- Implementar `E = f(N1, N2, N3, N4, Qe)` con pesos configurables y resultado JSONB
- Proveer 4 endpoints REST para métricas individuales y agregadas
- Dashboard docente con radar chart N1-N4 y tabla de alumnos
- Vista de progreso para el alumno (agregados, sin detalle que permita gaming)

**Non-Goals:**
- Alertas en tiempo real de riesgo (EPIC-15)
- Visualización de traza CTR completa (EPIC-16)
- Machine learning o predicción — los scores son deterministas basados en rúbrica
- Modificar el flujo de cierre de sesión de EPIC-13 — solo hookear post-close

## Decisions

### D1: Cálculo síncrono post-close vs. worker asíncrono

**Decisión**: Cálculo síncrono dentro de la misma transacción de `close_session()`.

**Alternativa considerada**: Worker asíncrono via Redis Stream `events:cognitive` con evento `session.closed`. Agrega complejidad (nuevo consumer, eventual consistency, manejo de errores), y las métricas son baratas de calcular — es conteo y aritmética sobre eventos ya cargados en memoria.

**Rationale**: El cierre ya carga los eventos para computar `session_hash`. Reusar esos datos evita un round-trip a DB. Si el cálculo falla, la transacción entera hace rollback — no hay sesiones cerradas sin métricas. Futuro: si el cálculo se vuelve costoso, se puede migrar a async sin cambiar la interfaz.

### D2: Dónde vive la lógica de scoring

**Decisión**: Nuevo service `MetricsEngine` en `app/features/evaluation/service.py`.

Separación:
- `MetricsEngine.compute(session, events)` → calcula todo y retorna `CognitiveMetrics` + score JSONB
- `CognitiveService.close_session()` llama a `MetricsEngine` después de sellar la cadena
- `MetricsEngine` NO conoce la DB — recibe datos, retorna objetos. El service que lo llama persiste.

**Rationale**: EPIC-14 es el dueño del módulo `evaluation/`. Mantener la lógica pura (sin I/O) facilita tests deterministas. `CognitiveService` solo persiste los resultados.

### D3: Estructura del módulo evaluation/

```
app/features/evaluation/
├── __init__.py
├── models.py          # CognitiveMetrics + ReasoningRecord
├── repositories.py    # CognitiveMetricsRepository
├── service.py         # MetricsEngine (cálculo puro)
├── schemas.py         # Pydantic DTOs para endpoints
├── router.py          # 4 endpoints REST
└── rubric.py          # Carga y parseo de rubrics/n4_anexo_b.yaml
```

### D4: Fórmula E = f(N1, N2, N3, N4, Qe)

**Decisión**: Pesos configurables via `rubrics/n4_anexo_b.yaml`. Defaults:

```yaml
weights:
  n1_comprehension: 0.15
  n2_strategy: 0.25
  n3_validation: 0.25
  n4_ai_interaction: 0.20
  qe: 0.15
```

El resultado NO es un escalar — es un JSONB profile:
```json
{
  "n1": 72.50, "n2": 68.00, "n3": 85.00, "n4": 55.00,
  "qe": 71.20,
  "weighted_total": 70.35,
  "weights": {"n1": 0.15, "n2": 0.25, "n3": 0.25, "n4": 0.20, "qe": 0.15},
  "risk_level": "medium",
  "computed_at": "2026-04-15T14:30:00Z"
}
```

Almacenado en `cognitive_sessions.n4_final_score`.

### D5: Cálculo de scores N1-N4

Cada score (0-100) se calcula contando eventos del nivel correspondiente y su calidad:

- **N1 (comprensión)**: proporción de eventos `reads_problem` + `code.snapshot` con engagement (no solo 1 lectura rápida). Factor: tiempo en problema.
- **N2 (estrategia)**: proporción de eventos `submission.created` con iteraciones previas de `code.run`. Factor: ratio intentos/ejecuciones.
- **N3 (validación)**: proporción de `code.run` con correcciones posteriores. Factor: progresión de errores (mejoran o se estancan).
- **N4 (interacción IA)**: calidad de preguntas al tutor basada en `n4_level` del payload. Penalización por `dependency_score` alto.

Base: `(event_count_for_level / total_events) * quality_factor * 100`, clamped 0-100.

### D6: Cálculo de Qe (calidad epistémica)

4 sub-scores (0-100 cada uno), promediados con pesos iguales:
- **qe_quality_prompt**: calidad de las preguntas al tutor (clasificación N4 ≥ N2 = buena)
- **qe_critical_evaluation**: presencia de eventos N3 post-respuesta del tutor
- **qe_integration**: ratio de ejecuciones exitosas post-ayuda del tutor
- **qe_verification**: presencia de `code.run` después de cambios (el alumno verifica)

### D7: Risk level

Derivado de las métricas calculadas:
- **critical**: dependency_score > 0.7 AND n4_ai_interaction_score < 30
- **high**: dependency_score > 0.5 OR any N-score < 20
- **medium**: any N-score < 40 OR qe_score < 40
- **low**: default

### D8: ReasoningRecord hash chain

Los `reasoning_records` extienden la evidencia inmutable del CTR. Usan el mismo patrón de hash chain que `cognitive_events`:
- `previous_hash`: hash del último reasoning_record de la sesión (o `session_hash` si es el primero)
- `event_hash`: `SHA256(previous_hash + ':' + record_type + ':' + json(details) + ':' + created_at_iso)`

Se crean durante el cálculo de métricas como evidencia de las decisiones del motor.

### D9: Endpoints y auth

| Endpoint | Método | Auth | Notas |
|----------|--------|------|-------|
| `/api/v1/cognitive/sessions/{id}/metrics` | GET | docente, admin | Métricas de una sesión |
| `/api/v1/teacher/courses/{id}/dashboard` | GET | docente (comisión propia), admin | Query param `commission_id` required, usa campo denormalizado |
| `/api/v1/teacher/students/{id}/profile` | GET | docente (comisión propia), admin | Perfil cognitivo agregado del alumno |
| `/api/v1/student/me/progress` | GET | alumno (solo sus datos) | Scores agregados, sin detalle que permita gaming |

### D10: Frontend — Recharts para radar chart

**Decisión**: Usar Recharts (ya es estándar en el ecosistema React) para el radar chart N1-N4 y gráficos de evolución.

Dashboard docente: página nueva en `/teacher/courses/:courseId/dashboard` con:
- Selector de comisión
- Radar chart promedio de la comisión
- Tabla de alumnos con mini-radars inline
- Filtros por ejercicio, período, risk level

Dashboard alumno: sección nueva en `/student/progress` con:
- Gráfico de evolución temporal (line chart con N1-N4 por sesión)
- Scores agregados actuales (cards)
- Sin desglose individual de sesiones (anti-gaming)

## Risks / Trade-offs

**[Cálculo síncrono en close_session lento]** → Con <100 eventos por sesión, el cálculo es <10ms. Si crece, migrar a async worker. Monitorear con logging de duración.

**[Rúbrica hardcoded vs. configurable]** → La rúbrica vive en YAML. Cambiar pesos NO requiere redeploy (se recarga al arrancar). Pero cambiar la lógica de scoring sí requiere código. Trade-off aceptable: la lógica cambia raramente, los pesos se ajustan.

**[NUMERIC vs FLOAT precision]** → NUMERIC(5,2) usa más storage que FLOAT pero evita errores de floating-point en comparaciones. Para métricas pedagógicas la precisión importa. Trade-off correcto.

**[ReasoningRecord como fase 1]** → El modelo se crea pero el poblado inicial es mínimo (1 record por sesión con el summary del cálculo). La lógica rica de hypothesis/strategy/validation se expande en EPICs futuras.

**[Dependencia Recharts en frontend]** → Nueva dependencia NPM. Alternativa: D3 directo (más control, más código). Recharts es más pragmático para radar charts estándar.

## Migration Plan

1. Migración Alembic: crear tablas `cognitive.cognitive_metrics` y `cognitive.reasoning_records`
2. Deploy backend: MetricsEngine + endpoints. Las sesiones ya cerradas no tienen métricas — se pueden recalcular con un script one-off si se necesita.
3. Deploy frontend: dashboards consumen endpoints nuevos.
4. Rollback: drop tablas nuevas, revertir código. No hay datos legacy afectados.

## Open Questions

- **Recálculo retroactivo**: ¿se recalculan métricas para sesiones cerradas pre-EPIC-14? → Decisión: no por ahora, solo sesiones nuevas. Script de backfill disponible si se necesita.
- **Cacheo de aggregations**: ¿Redis cache para el dashboard docente? → Decisión: no en EPIC-14. Si la query es lenta, se agrega en un cambio posterior.
