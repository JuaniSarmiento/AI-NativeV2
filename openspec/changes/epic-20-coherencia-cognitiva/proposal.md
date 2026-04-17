## Why

El sistema de trazabilidad cognitiva tiene la arquitectura técnica correcta (hash chain, event bus, consumer) pero la interpretación cognitiva presenta 16 deficiencias que comprometen la validez del modelo evaluativo de la tesis. Los scores N1-N4 son mutuamente excluyentes por diseño matemático, no existen las tres coherencias del modelo teórico (temporal, código-discurso, inter-iteración), hay eventos que van a streams sin consumidor, clasificación N4 hardcodeada, y no se distinguen los tipos de prompts del alumno (exploratorio/verificador/generativo). Sin estas correcciones, el sistema no puede sustentar las inferencias evaluativas que el modelo teórico propone.

## What Changes

### Fase A — Bugfixes
- Eliminar emisión redundante de eventos `cognitive.classified` del TutorService
- Corregir CognitiveEventClassifier para leer `n4_level` del payload en tutor events (hoy hardcodea N4=4)
- Fix endpoint `/sessions/{id}/trace` para devolver timeline + chat + code_evolution (hoy vacíos)
- Implementar `reflection_score` en MetricsEngine (hoy siempre None)
- Fix `qe_score_max` en risk level medium (hoy es un `pass`)
- Fix `qe_critical_evaluation` para medir runs después de CADA tutor response (hoy solo mira el último)
- Fix `commission_id` fallback: error en vez de UUID cero

### Fase B — Scoring independiente + clasificación híbrida
- Agregar `prompt_type` (exploratory/verifier/generative) al N4Classifier y al payload de outbox events
- Clasificador híbrido en consumer: regex → LLM (3s timeout) → fallback a regex
- Rediseñar scores N1-N4 como evaluaciones independientes de cada dimensión (no proporciones sobre total)
- Actualizar rúbrica con nuevos parámetros

### Fase C — Coherence Engine
- Nuevo `CoherenceEngine`: coherencia temporal, código-discurso, consistencia inter-iteración
- Integración en MetricsEngine al cierre de sesión
- Nuevos campos en `cognitive_metrics` + migración Alembic

## Capabilities

### New Capabilities
- `coherence-engine`: Motor de análisis de coherencia cognitiva — temporal, código-discurso, inter-iteración. Computa scores y detecta anomalías al cierre de sesión.
- `hybrid-classifier`: Clasificación híbrida N4 en el consumer — regex con escalamiento a LLM cuando la confianza es baja. Incluye prompt_type classification.

### Modified Capabilities
- `n4-classifier`: Agrega prompt_type (exploratory/verifier/generative) a la clasificación de mensajes
- `evaluation-engine`: Scoring N1-N4 independiente (no proporcional), reflection_score, fixes de Qe, integración de CoherenceEngine
- `cognitive-worker`: Integra clasificador híbrido, corrige lectura de n4_level del payload
- `tutor-events`: Elimina emisión de cognitive.classified, agrega prompt_type al payload
- `cognitive-trace-api`: Fix TraceResponse para devolver datos completos
- `cognitive-metrics-model`: Nuevos campos de coherencia + prompt_type_distribution

## Impact

- **Backend**: 12 archivos modificados, 1 nuevo (evaluation/coherence.py), 1 migración Alembic
- **Archivos core**: tutor/service.py, tutor/n4_classifier.py, cognitive/classifier.py, cognitive/consumer.py, cognitive/router.py, evaluation/service.py, evaluation/rubric.py
- **DB**: ALTER TABLE cognitive_metrics ADD 5 columnas (3 scores + anomalies JSONB + prompt_type_distribution JSONB)
- **Event Bus**: Se deja de emitir cognitive.classified al stream events:cognitive
- **Dependencia nueva**: LLM adapter en consumer (Mistral/Haiku para clasificación híbrida)
- **APIs afectadas**: GET /sessions/{id}/trace (fix), GET /sessions/{id}/metrics (campos nuevos)
- **No hay breaking changes** — los campos nuevos son NULLABLE, los endpoints existentes siguen funcionando
