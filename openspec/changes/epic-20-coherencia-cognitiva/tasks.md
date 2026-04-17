## 1. Fase A — Bugfixes (tutor-events, cognitive-worker, cognitive-trace-api, evaluation-engine)

- [x] 1.1 Eliminar emisión de eventos `cognitive.classified` del TutorService (`tutor/service.py` líneas 193-211) — spec: tutor-events/REMOVED
- [x] 1.2 Emitir `tutor.interaction.completed` para el user turn (hoy solo se emite para assistant) — spec: tutor-events/MODIFIED
- [x] 1.3 Corregir CognitiveEventClassifier: leer `payload.n4_level` para tutor.interaction.completed en vez de hardcodear N4=4, fallback a 4 si no existe — spec: cognitive-worker
- [x] 1.4 Fix TraceResponse: refactorizar `get_session_trace()` en `cognitive/router.py` para llamar a `service.get_trace()` y mapear timeline + chat + code_evolution — spec: cognitive-trace-api
- [x] 1.5 Implementar `reflection_score` en MetricsEngine: computar desde eventos `reflection.submitted` (campos completados, difficulty_perception, confidence_level) — spec: evaluation-engine
- [x] 1.6 Fix `qe_score_max` en `_derive_risk_level()`: evaluar qe_score contra threshold medium en vez de `pass` — spec: evaluation-engine
- [x] 1.7 Fix `qe_critical_evaluation`: medir runs después de CADA `tutor.response_received`, no solo el último — spec: evaluation-engine
- [x] 1.8 Fix commission_id: en consumer, rechazar eventos con UUID cero y logear warning — spec: cognitive-worker
- [x] 1.9 Tests Fase A: un test por cada bugfix que reproduce el bug antes del fix

## 2. Fase B — Prompt Type + Clasificación Híbrida (n4-classifier, hybrid-classifier, evaluation-engine)

- [x] 2.1 Agregar `prompt_type` al N4ClassificationResult dataclass y al N4Classifier con regex patterns (exploratory/verifier/generative) — spec: n4-classifier
- [x] 2.2 Agregar `prompt_type` al payload de `tutor.interaction.completed` en TutorService — spec: tutor-events
- [x] 2.3 Crear LLM classification prompt y función `llm_classify_message()` en `cognitive/classifier.py` — spec: hybrid-classifier
- [x] 2.4 Integrar clasificador híbrido en `CognitiveEventConsumer._process_event()`: regex → LLM (3s timeout) → fallback — spec: hybrid-classifier
- [x] 2.5 Rediseñar `_compute_n1()`: scoring independiente basado en presencia + profundidad + calidad — spec: evaluation-engine
- [x] 2.6 Rediseñar `_compute_n2()`: scoring independiente basado en evidencia de estrategia — spec: evaluation-engine
- [x] 2.7 Rediseñar `_compute_n3()`: scoring independiente basado en calidad de validación iterativa — spec: evaluation-engine
- [x] 2.8 Rediseñar `_compute_n4()`: scoring basado en prompt_type distribution + dependency — spec: evaluation-engine
- [x] 2.9 Actualizar `rubrics/n4_anexo_b.yaml` con nuevos parámetros de scoring independiente y thresholds — spec: evaluation-engine
- [x] 2.10 Tests Fase B: scoring determinista con sesiones de referencia, prompt_type classification, mock LLM hybrid

## 3. Fase C — Coherence Engine (coherence-engine, cognitive-metrics-model)

- [x] 3.1 Migración Alembic: ADD columns temporal_coherence_score, code_discourse_score, inter_iteration_score (NUMERIC(5,2)), coherence_anomalies (JSONB), prompt_type_distribution (JSONB) a cognitive_metrics — spec: cognitive-metrics-model
- [x] 3.2 Actualizar modelo CognitiveMetrics con los 5 campos nuevos — spec: cognitive-metrics-model
- [x] 3.3 Crear `evaluation/coherence.py` con CoherenceEngine (puro Python, sin I/O) y CoherenceResult dataclass — spec: coherence-engine
- [x] 3.4 Implementar coherencia temporal: análisis de secuencias N-level, detección de anomalías (solution_without_comprehension, pure_delegation) — spec: coherence-engine
- [x] 3.5 Implementar coherencia código-discurso: cruce keywords chat ↔ diffs de código — spec: coherence-engine
- [x] 3.6 Implementar consistencia inter-iteración: análisis de magnitud de diffs, detección de integración acrítica — spec: coherence-engine
- [x] 3.7 Integrar CoherenceEngine en CognitiveService.close_session(): cargar snapshots + chat, llamar engine, persistir resultados — spec: evaluation-engine
- [x] 3.8 Computar y persistir prompt_type_distribution en cognitive_metrics al cierre — spec: cognitive-metrics-model
- [x] 3.9 Actualizar CognitiveMetricsResponse y TraceResponse schemas con campos de coherencia — spec: cognitive-trace-api
- [x] 3.10 Tests Fase C: coherencia temporal con secuencias anómalas, código-discurso con pares conocidos, inter-iteración con diffs masivos, integración completa
