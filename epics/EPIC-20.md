# EPIC-20: Coherencia Cognitiva — Clasificación Híbrida, Scoring Independiente y Análisis de Coherencia

> **Issue**: #20 | **Milestone**: Fase 3 — Motor Cognitivo | **Labels**: epic, fase-3, priority:critical

**Nivel de gobernanza**: CRITICAL — modifica constructos evaluativos del modelo N4

## Contexto

El sistema de trazabilidad cognitiva tiene la arquitectura técnica correcta (hash chain, event bus, consumer pattern, separación de schemas) pero la INTERPRETACIÓN cognitiva de los datos presenta deficiencias graves que comprometen la validez del modelo evaluativo:

1. **El clasificador N4 es regex puro** — techo de precisión bajo, sin capacidad de interpretar contexto
2. **Los scores N1-N4 son mutuamente excluyentes** — una proporción sobre total de eventos, no una medida independiente de cada dimensión
3. **No existen las tres coherencias** del modelo teórico: temporal, código-discurso, inter-iteración
4. **Eventos perdidos**: `cognitive.classified` va a un stream sin consumidor
5. **Clasificación hardcodeada**: el CognitiveEventClassifier asigna N4=4 fijo a todos los tutor events
6. **Tipificación de prompts incompleta**: no distingue exploratorio/verificador/generativo (dimensión central del modelo N4)
7. **Bugs en el MetricsEngine**: reflection_score siempre None, qe_score_max no se usa, qe_critical_evaluation solo mira último response
8. **TraceResponse incompleta**: timeline y chat vacíos en el endpoint de traza
9. **commission_id fallback a UUID cero** cuando el enrollment lookup falla

Esta EPIC corrige todos estos problemas en tres fases internas secuenciales: primero los bugs, luego el modelo de scoring, luego el análisis de coherencia.

## Decisiones arquitectónicas

### Clasificación Híbrida (Opción A — pre-persistencia)

El consumer clasifica ANTES de persistir en el CTR. Flujo:

```
Evento llega al Consumer
    │
    ▼
Regex Pass (existente, ~0ms)
    │
    ├── confidence == HIGH → persiste con nivel regex
    │
    └── confidence == LOW → LLM classify (3s timeout)
         │
         ├── LLM responde → persiste con nivel LLM
         └── LLM timeout  → persiste con nivel regex (fallback)
```

**Justificación**: El CTR es inmutable y hash-chained. El n4_level vive en el payload que se hashea. Si clasificamos después, o cambiamos el nivel posterior, rompemos la cadena. Clasificar antes garantiza que el CTR tiene el dato correcto desde el momento cero.

El consumer ya corre en background (no bloquea al alumno). El LLM call agrega ~1-3s de latencia al procesamiento del evento, no al chat del alumno.

### Scoring Independiente (no proporcional)

Los scores N1-N4 dejan de ser `count(tipo) / total_events` y pasan a ser evaluaciones independientes de cada dimensión:

- **N1**: ¿Hubo evidencia de comprensión? (presencia de reads_problem + tiempo de engagement + reformulación en chat)
- **N2**: ¿Hubo estrategia deliberada? (eventos pre-codificación, elección de estructura en chat, planificación antes de ejecución)
- **N3**: ¿Hubo validación iterativa? (ciclos de run→error→fix→run, convergencia de tests, diseño de pruebas)
- **N4**: ¿La interacción con IA fue reflexiva? (prompt_type exploratory/verifier vs generative, dependency_score, integración crítica)

Cada score evalúa PRESENCIA y CALIDAD de la dimensión, no proporción relativa. Un alumno que comprende bien, planifica, testea mucho y usa bien la IA puede tener scores altos en las 4 dimensiones simultáneamente.

### Coherencias al cierre de sesión

Las tres coherencias se computan una sola vez, al cerrar la sesión, junto con los scores N1-N4 y Qe. Un único punto de cómputo, un único punto de verdad. Se persisten en `cognitive_metrics` (campos nuevos).

### Eliminación de `cognitive.classified` events

Los eventos `cognitive.classified` que emite TutorService son redundantes — el n4_level fino ya viaja en el payload de `tutor.interaction.completed`. Se eliminan del TutorService. El `events:cognitive` stream deja de recibir estos eventos.

## Alcance

### Fase A — Bugfixes y gaps de implementación

Correcciones que no cambian la arquitectura ni el modelo evaluativo:

1. **Eliminar emisión de `cognitive.classified`** del TutorService (líneas 193-211 de `tutor/service.py`)
2. **Corregir CognitiveEventClassifier** para leer `n4_level` del payload en vez de hardcodear N4=4 para tutor events
3. **Corregir TraceResponse**: el endpoint `GET /sessions/{id}/trace` debe llamar a `service.get_trace()` que SÍ ensambla timeline + chat + code_evolution
4. **Implementar reflection_score**: computar desde eventos `reflection.submitted` en el payload (difficulty_perception, confidence_level, campos completados)
5. **Corregir qe_score_max**: implementar el check de Qe en `_derive_risk_level()` para nivel medium (actualmente es un `pass`)
6. **Corregir qe_critical_evaluation**: medir runs después de CADA tutor response, no solo del último
7. **Corregir commission_id fallback**: lanzar `ValidationError` cuando no se puede resolver, en vez de usar UUID cero. Si el evento viene sin commission_id válido, logear warning y descartar (no crear sesiones con datos inválidos)

### Fase B — Scoring independiente y tipificación de prompts

Cambios al modelo evaluativo que requieren revisión de gobernanza:

8. **Agregar prompt_type al N4Classifier**: clasificar cada mensaje del alumno como `exploratory` (busca comprender), `verifier` (contrasta hipótesis) o `generative` (pide código). Agrega regex patterns para cada tipo. El prompt_type viaja en el payload del outbox event junto con n4_level y sub_classification.
9. **Clasificador Híbrido en el Consumer**: cuando el regex tiene confidence=LOW, hacer un LLM call ligero (Haiku/Mistral-small, max 50 tokens, prompt mínimo) para reclasificar. Timeout 3 segundos, fallback a regex.
10. **Rediseñar _compute_n1**: score basado en presencia y profundidad de comprensión, no en proporción. Factores: ¿leyó el problema? ¿tardó >10s antes de codear? ¿hay evidencia de reformulación en tutor questions N1?
11. **Rediseñar _compute_n2**: score basado en evidencia de estrategia deliberada. Factores: ¿hay eventos de planificación antes de code.run? ¿hubo preguntas N2 al tutor? ¿eligió estructura de datos antes de implementar?
12. **Rediseñar _compute_n3**: score basado en calidad de validación iterativa. Factores: ¿cuántos ciclos run→fix→run? ¿convergieron los tests? ¿hubo correction progresiva (errors decrecen)?
13. **Rediseñar _compute_n4**: score basado en calidad de interacción con IA. Factores: distribución de prompt_type (exploratory+verifier vs generative), dependency_score, integración crítica post-tutor.
14. **Actualizar rúbrica**: `rubrics/n4_anexo_b.yaml` con nuevos parámetros de scoring independiente.

### Fase C — Coherence Engine

El componente nuevo que implementa las tres coherencias del modelo teórico:

15. **CoherenceEngine** — módulo nuevo en `app/features/evaluation/coherence.py`, puro Python sin I/O (como MetricsEngine). Recibe eventos, snapshots y chat como input.

16. **Coherencia temporal**: analiza secuencias de niveles N en el CTR.
    - Mide: ¿aparecen los niveles en secuencias cognitivamente coherentes?
    - Anomalías: solución sin comprensión previa (N3 sin N1), solo delegación (N4 dominante sin N1/N2/N3), saltos nivel sin transición
    - Score 0-100 basado en presencia de transiciones esperadas y ausencia de anomalías

17. **Coherencia código-discurso**: cruza contenido del chat con diffs de código.
    - Mide: ¿lo que el alumno dice/pregunta se refleja en los cambios de código?
    - Detecta: dice "voy a usar recursión" pero el código no cambia; dice que entendió pero el código no refleja comprensión
    - Implementación: para cada code.snapshot posterior a un tutor exchange, verificar si los cambios son coherentes con lo discutido (heurística basada en keywords del chat que aparecen como identifiers/patterns en el diff)
    - Score 0-100

18. **Consistencia inter-iteración**: analiza la trayectoria de cambios de código.
    - Mide: ¿los cambios sucesivos muestran progresión coherente?
    - Detecta integración acrítica: diffs masivos (>N líneas) sin actividad previa de comprensión/estrategia, velocidad anómala de escritura (muchas líneas en poco tiempo sin errores), cambio abrupto de estilo/naming
    - Score 0-100

19. **Integración en MetricsEngine**: el `CoherenceEngine.compute()` se llama dentro de `MetricsEngine.compute()` al cierre de sesión. Los tres scores se persisten en campos nuevos de `cognitive_metrics`.

20. **Migración Alembic**: agregar campos a `cognitive_metrics`:
    - `temporal_coherence_score` (NUMERIC(5,2), NULLABLE)
    - `code_discourse_score` (NUMERIC(5,2), NULLABLE)
    - `inter_iteration_score` (NUMERIC(5,2), NULLABLE)
    - `coherence_anomalies` (JSONB, NULLABLE) — array de anomalías detectadas con tipo, descripción y event_ids de evidencia
    - `prompt_type_distribution` (JSONB, NULLABLE) — `{exploratory: N, verifier: N, generative: N}`

## Contratos

### Modifica
- `cognitive/classifier.py` — lee n4_level del payload para tutor events + LLM fallback
- `cognitive/consumer.py` — integra clasificador híbrido (regex → LLM con timeout)
- `cognitive/router.py` — endpoint trace llama a service.get_trace() correctamente
- `tutor/service.py` — elimina emisión de cognitive.classified, agrega prompt_type al payload
- `tutor/n4_classifier.py` — agrega prompt_type classification (exploratory/verifier/generative)
- `evaluation/service.py` — scoring independiente, reflection_score, qe fixes, integración CoherenceEngine
- `evaluation/rubric.py` + `rubrics/n4_anexo_b.yaml` — nuevos parámetros de rúbrica

### Crea
- `evaluation/coherence.py` �� CoherenceEngine (temporal, código-discurso, inter-iteración)
- Migración Alembic para campos nuevos en `cognitive_metrics`

### Consume
- Sesiones cognitivas cerradas con todos sus eventos (de EPIC-13)
- Code snapshots (de EPIC-08) — para coherencia código-discurso e inter-iteración
- Tutor interactions (de EPIC-09) — para coherencia código-discurso
- Reflections (de EPIC-12) — para reflection_score

### Produce
- Scores de coherencia en `cognitive_metrics` (3 scores + anomalías + prompt_type_distribution)
- Scoring N1-N4 corregido (independiente, no proporcional)
- Reflection score computado
- Clasificación híbrida más precisa en el CTR

## Dependencias
- **Blocked by**: EPIC-13 (CTR), EPIC-14 (MetricsEngine existente), EPIC-08 (snapshots), EPIC-09 (tutor interactions), EPIC-12 (reflections)
- **Blocks**: EPIC-16 (la traza visual consume los scores de coherencia y anomalías), EPIC-15 (risk detection puede incorporar coherencia como factor de riesgo)

## Archivos afectados

| Archivo | Cambio | Fase |
|---------|--------|------|
| `tutor/service.py` | Eliminar cognitive.classified, agregar prompt_type al payload | A |
| `tutor/n4_classifier.py` | Agregar prompt_type classification | B |
| `cognitive/classifier.py` | Leer n4_level del payload + soporte LLM híbrido | A+B |
| `cognitive/consumer.py` | Integrar LLM adapter para clasificación híbrida | B |
| `cognitive/router.py` | Fix trace endpoint para usar service.get_trace() | A |
| `evaluation/service.py` | Scoring independiente, reflection_score, qe fixes, coherence | A+B+C |
| `evaluation/coherence.py` | **NUEVO** — CoherenceEngine | C |
| `evaluation/rubric.py` | Nuevos parámetros de rúbrica | B |
| `rubrics/n4_anexo_b.yaml` | Nuevos parámetros de rúbrica | B |
| `evaluation/schemas.py` | Campos de coherencia en CognitiveMetricsResponse | C |
| `cognitive/schemas.py` | TraceResponse incluye coherencia y anomalías | C |
| `alembic/versions/0XX_*.py` | Migración campos nuevos cognitive_metrics | C |

## Stories

### Fase A — Bugfixes (no requiere revisión de gobernanza)
- [ ] Eliminar emisión de eventos `cognitive.classified` del TutorService
- [ ] Corregir CognitiveEventClassifier: leer n4_level del payload para tutor.interaction.completed
- [ ] Fix TraceResponse: endpoint trace usa service.get_trace() (timeline + chat + code_evolution)
- [ ] Implementar reflection_score en MetricsEngine
- [ ] Fix qe_score_max en _derive_risk_level() para nivel medium
- [ ] Fix qe_critical_evaluation: medir runs después de CADA tutor response
- [ ] Fix commission_id: ValidationError en vez de UUID cero
- [ ] Tests: cada bugfix con test que reproduce el bug antes del fix

### Fase B — Scoring independiente + clasificación híbrida (requiere revisión MEDIUM)
- [ ] Agregar prompt_type (exploratory/verifier/generative) al N4Classifier
- [ ] Agregar prompt_type al payload del outbox event tutor.interaction.completed
- [ ] Implementar clasificador híbrido en CognitiveEventConsumer (regex → LLM con 3s timeout)
- [ ] Rediseñar _compute_n1: presencia y profundidad de comprensión
- [ ] Rediseñar _compute_n2: evidencia de estrategia deliberada
- [ ] Rediseñar _compute_n3: calidad de validación iterativa
- [ ] Rediseñar _compute_n4: distribución prompt_type + dependency + integración crítica
- [ ] Actualizar rúbrica n4_anexo_b.yaml con nuevos parámetros
- [ ] Tests: scoring determinista con sesiones de referencia conocidas
- [ ] Tests: prompt_type classification con corpus de mensajes etiquetados
- [ ] Tests: clasificador híbrido con mock LLM (timeout, success, fallback)

### Fase C — Coherence Engine (requiere revisión CRITICAL)
- [ ] Migración Alembic: campos de coherencia en cognitive_metrics
- [ ] CoherenceEngine: coherencia temporal (secuencias N-level, anomalías)
- [ ] CoherenceEngine: coherencia código-discurso (chat ↔ diffs)
- [ ] CoherenceEngine: consistencia inter-iteración (trayectoria de código, detección integración acrítica)
- [ ] Integrar CoherenceEngine en MetricsEngine.compute() al cierre de sesión
- [ ] Persistir coherence scores + anomalías en cognitive_metrics
- [ ] Actualizar TraceResponse y CognitiveMetricsResponse con campos de coherencia
- [ ] Tests: coherencia temporal con secuencias anómalas conocidas
- [ ] Tests: coherencia código-discurso con pares chat-diff conocidos
- [ ] Tests: consistencia inter-iteración con diffs masivos vs graduales
- [ ] Tests: integración completa — sesión cerrada produce todos los scores

## Criterio de Done

### Fase A
- Todos los bugs listados corregidos con tests que los reproducen
- TraceResponse devuelve timeline, chat y code_evolution completos
- reflection_score se computa correctamente desde reflexiones del alumno
- No se emiten eventos cognitive.classified redundantes
- CognitiveEventClassifier usa n4_level del payload para tutor events

### Fase B
- Cada mensaje del alumno al tutor tiene un prompt_type (exploratory/verifier/generative)
- El consumer clasifica con LLM cuando regex tiene baja confianza (con fallback a 3s)
- Scores N1-N4 son independientes: un alumno completo puede tener 4 scores altos simultáneamente
- Rúbrica actualizada con parámetros de scoring independiente
- Tests deterministas con sesiones de referencia pasan

### Fase C
- Coherencia temporal: detecta secuencias anómalas (solución sin comprensión, solo delegación)
- Coherencia código-discurso: detecta discrepancias entre lo dicho y lo programado
- Consistencia inter-iteración: detecta integración acrítica de código externo (diffs masivos sin actividad previa)
- Tres scores de coherencia se persisten en cognitive_metrics al cierre de sesión
- Anomalías se registran con tipo, descripción y event_ids de evidencia
- Endpoint de traza incluye scores de coherencia y anomalías
- Tests de integración completa pasan

## Referencia
- Documento maestro: constructos de coherencia estructural (temporal, código-discurso, inter-iteración)
- Documento maestro: tipificación de prompts (exploratorio, verificador, generativo)
- Documento maestro: función evaluativa E = f(N1, N2, N3, N4, Qe)
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md`
- `rubrics/n4_anexo_b.yaml`
- Análisis de problemas: 16 deficiencias identificadas en sesión 2026-04-17
