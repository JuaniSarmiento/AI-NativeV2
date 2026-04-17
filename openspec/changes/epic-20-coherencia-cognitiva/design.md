## Context

EPICs 1-15 implementadas. El CTR (Cognitive Trace Record) funciona: hash chain, event bus consumer, clasificación básica. Pero el modelo evaluativo es superficial — scores proporcionales mutuamente excluyentes, sin análisis de coherencia, sin tipificación de prompts, con varios bugs. La tesis requiere que cada inferencia evaluativa tenga procedencia auditable hasta los datos brutos.

Estado actual del pipeline:
```
Evento raw → OutboxWorker → Redis Stream → CognitiveEventConsumer
  → CognitiveEventClassifier (mapeo estático) → CognitiveService.add_event()
  → [al cierre] MetricsEngine.compute() → cognitive_metrics
```

## Goals / Non-Goals

**Goals:**
- Corregir 7 bugs que degradan la trazabilidad (Fase A)
- Scores N1-N4 que evalúen cada dimensión de forma independiente (Fase B)
- Tipificación de prompts exploratorio/verificador/generativo (Fase B)
- Clasificación híbrida regex→LLM en el consumer (Fase B)
- Análisis de coherencia temporal, código-discurso, inter-iteración (Fase C)
- Mantener inmutabilidad del CTR y integridad del hash chain

**Non-Goals:**
- Métricas incrementales / snapshots parciales durante sesión abierta
- Reentrenamiento del clasificador con datos del piloto (post-tesis)
- UI de coherencia en el frontend (eso es EPIC-16)
- Cambios al hash chain formula (el prompt_hash ya viaja en el payload hasheado)

## Decisions

### D1: Clasificación pre-persistencia (Opción A)

El LLM classify ocurre DENTRO del consumer, ANTES de `add_event()`.

**Alternativas descartadas:**
- Opción B (tabla de anotaciones separada): complejidad innecesaria, hay que mergear en queries
- Opción C (dos campos en payload): semántica confusa, dos verdades por evento

**Implementación:** En `CognitiveEventConsumer._process_event()`, después de `classifier.classify()`:
```
si confidence == LOW y event es tutor.interaction.completed:
    n4_level = await llm_reclassify(payload.content, timeout=3s)
    si timeout → usar nivel regex
    classified.payload["n4_level"] = n4_level
```

El LLM adapter reutiliza el existente (MistralAdapter) con un prompt mínimo de clasificación (~100 tokens input, ~10 tokens output). No es streaming.

### D2: Scoring independiente con indicadores de presencia + calidad

Cada score N1-N4 se computa como combinación de:
- **Presencia**: ¿hay evidencia de esta dimensión? (binario 0/1)
- **Profundidad**: ¿cuánta evidencia? (cantidad de señales)
- **Calidad**: ¿qué tan buena es la evidencia? (factores cualitativos)

Score = `presencia * (profundidad_normalizada * peso_profundidad + calidad * peso_calidad) * 100`

Cada dimensión tiene su propio denominador o benchmark — NO comparten un denominador común (total_events), eliminando la exclusión mutua.

### D3: CoherenceEngine como módulo puro Python

Igual que MetricsEngine: sin I/O, sin async, sin FastAPI. Recibe datos pre-cargados como input.

```python
class CoherenceEngine:
    def compute(self, events, snapshots, chat_messages) -> CoherenceResult
```

Se invoca desde `CognitiveService.close_session()` junto con `MetricsEngine.compute()`. Los snapshots y chat_messages se cargan previamente con queries del service.

### D4: Prompt type classification con regex + extensión de patterns

Se agregan patterns al N4Classifier existente:

- **exploratory**: "cómo funciona", "por qué", "qué pasa si", "explicame"
- **verifier**: "está bien mi...", "es correcto", "lo hice bien", "funciona?"
- **generative**: "hacé vos", "dame el código", "escribime", "resolvelo"

El prompt_type viaja en el payload de `tutor.interaction.completed` junto con n4_level y sub_classification.

### D5: Coherencia código-discurso por heurística de keywords

No se usa NLP semántico (sería over-engineering para el piloto). Se extraen keywords del chat del alumno (sustantivos técnicos: "recursión", "for", "lista", "diccionario", etc.) y se verifican contra los diffs de código posteriores. Score basado en tasa de coincidencia.

### D6: Detección de integración acrítica por magnitud de diff

Si un code.snapshot tiene un diff de >50 líneas netas y no hubo eventos N1/N2/N3 en los últimos 5 minutos, se marca como anomalía de "possible external integration". El threshold es configurable en la rúbrica.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| LLM classify agrega latencia al consumer | Timeout 3s + fallback a regex. Consumer no bloquea al alumno. |
| LLM classify agrega costo | Solo para confidence=LOW (~30% de mensajes). Prompt mínimo ~100 tokens. |
| Scoring independiente puede inflar scores | Cada dimensión tiene un cap de 100, y los quality_factors penalizan evidencia superficial. |
| Coherencia código-discurso con keywords es ruidosa | Es heurística, no determinista. Se reporta como score con anomalías, no como veredicto. |
| Migración ALTER TABLE en cognitive_metrics | Todos campos NULLABLE, no requiere backfill. Sesiones existentes mantienen NULL en campos nuevos. |
| Regex prompt_type puede clasificar mal | Es primera iteración. El prompt_type tiene sub_classification como respaldo. Se puede refinar con datos del piloto. |
