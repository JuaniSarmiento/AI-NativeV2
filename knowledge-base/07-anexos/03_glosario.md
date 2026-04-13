# Glosario del Dominio

**Plataforma AI-Native | UTN FRM**
Última actualización: 2026-04-10

---

Este glosario define los conceptos centrales del dominio de la plataforma, extraídos y formalizados a partir del documento de empate3 (tesis doctoral). Los términos aquí definidos son la fuente de verdad conceptual del proyecto. Cuando haya ambigüedad en el código, referirse a este glosario.

---

## Sistema AI-Native

**Definición**: Plataforma educativa diseñada desde su concepción para incorporar inteligencia artificial como componente estructural del proceso de aprendizaje, no como herramienta accesoria. En un sistema AI-Native, la IA no reemplaza al docente ni al estudiante, sino que actúa como mediador socrático que potencia el desarrollo cognitivo.

**Distinción clave**: Un sistema AI-Native se diferencia de uno que simplemente "usa IA" en que:
1. La IA está integrada en el modelo pedagógico desde el diseño.
2. El sistema registra y analiza cómo el estudiante interactúa con la IA.
3. La interacción con IA es evidencia de proceso, no solo de resultado.

**En el código**: El sistema en su totalidad. La plataforma UTN FRM que combina el tutor socrático, el registro de trazabilidad cognitiva, y el motor de evaluación N4.

---

## Trazabilidad Cognitiva

**Definición**: Capacidad del sistema para registrar, preservar y analizar el proceso mental del estudiante durante la resolución de un problema de programación. La trazabilidad cognitiva va más allá del resultado final (el código) para capturar el camino intelectual recorrido: los errores cometidos, las preguntas formuladas, las hipótesis planteadas, y el uso (o no uso) de la inteligencia artificial.

**Componentes de la trazabilidad**:
1. **Registro de acciones**: cada interacción significativa se guarda como un CTR.
2. **Cadena de integridad**: los registros están encadenados con hash para garantizar que no fueron alterados.
3. **Análisis de patrones**: los registros se procesan para determinar el nivel cognitivo del estudiante.

**Importancia pedagógica**: La trazabilidad permite evaluar el proceso de aprendizaje y no solo el producto final. Un alumno que llega a la solución correcta después de un proceso rico de exploración y error tiene mayor valor cognitivo que uno que copia la solución.

**En el código**: Implementada en el schema `cognitive` de PostgreSQL, principalmente en la tabla `cognitive_events`. El servicio `ctr_service.py` gestiona la creación y consulta de estos registros.

---

## Modelo N4 (N1, N2, N3, N4)

**Definición**: Taxonomía de cuatro niveles para clasificar la profundidad del procesamiento cognitivo de un estudiante durante la resolución de un problema. Basado en adaptaciones de la Taxonomía de Bloom aplicadas específicamente al contexto de programación y uso de IA.

**Referencia rápida de niveles**:
- **N1** = Comprensión (memorización, reconocimiento, reproducción)
- **N2** = Estrategia (comprensión, explicación, establecimiento de relaciones)
- **N3** = Validación (aplicación, resolución, evaluación de trade-offs)
- **N4** = Interacción con IA (síntesis crítica, metacognición, cuestionamiento del tutor)

### Nivel N1 — Comprensión (Memorización y Reconocimiento)

**Descripción**: El estudiante reproduce información sin transformarla. Copia sintaxis, repite patrones previamente vistos, o sigue instrucciones paso a paso sin comprensión.

**Indicadores en los CTRs**:
- Solicita al tutor que le dé el código directamente.
- Sus preguntas son del tipo "¿cómo se escribe X?".
- Copia fragmentos del historial de conversación en el editor.
- El código enviado es idéntico a ejemplos dados en clase.

**Implicación pedagógica**: No es un nivel malo per se (es necesario en las primeras etapas), pero si persiste en semestres avanzados indica dependencia.

### Nivel N2 — Estrategia (Comprensión y Explicación)

**Descripción**: El estudiante puede explicar conceptos con sus propias palabras, identificar errores básicos, y establecer relaciones entre conceptos conocidos.

**Indicadores en los CTRs**:
- Sus preguntas muestran que entendió el enunciado y puede reformularlo.
- Identifica qué parte de su código está fallando (aunque no sabe cómo arreglarlo).
- Puede explicar al tutor qué intenta hacer, aunque no lo logre implementar.
- Hace preguntas de "¿por qué?" además de "¿cómo?".

### Nivel N3 — Validación (Aplicación y Resolución)

**Descripción**: El estudiante puede aplicar conceptos conocidos a nuevos problemas, seleccionar la herramienta adecuada para cada situación, y depurar errores no triviales.

**Indicadores en los CTRs**:
- Evalúa múltiples enfoques antes de elegir uno.
- Sus preguntas al tutor son sobre trade-offs ("¿es mejor usar un diccionario o una lista aquí?").
- Corrige errores de forma autónoma entre intentos.
- Usa el tutor para validar su razonamiento, no para obtener la solución.

### Nivel N4 — Interacción con IA (Síntesis Crítica y Metacognición)

**Descripción**: El estudiante puede crear soluciones originales, evaluar críticamente el uso de IA, y reflexionar sobre su propio proceso de aprendizaje.

**Indicadores en los CTRs**:
- Cuestiona las sugerencias del tutor y las contrasta con su propio razonamiento.
- Identifica las limitaciones de la IA en el contexto del problema.
- Puede explicar por qué eligió un enfoque sobre otro con argumentos técnicos.
- Propone variantes o mejoras a su propia solución.
- Muestra consciencia de sus propias limitaciones ("sé que no entiendo bien la recursión todavía").

**En el código**: El `scoring_service.py` implementa el algoritmo de clasificación N1-N4 basado en los patrones detectados en los CTRs. Los resultados se almacenan en el schema `analytics`.

---

## Calidad Epistémica (Qe)

**Definición**: Métrica compuesta que cuantifica la profundidad y autonomía del proceso de aprendizaje del estudiante en una sesión dada. Es el indicador primario del valor cognitivo de una sesión de resolución de ejercicios.

**Fórmula conceptual**:
```
Qe = f(nivel_N4, autonomia_cognitiva, uso_critico_IA, riqueza_de_proceso)
```

Donde:
- `nivel_N4`: distribución de los eventos cognitivos en los niveles N1-N4
- `autonomia_cognitiva`: porcentaje del proceso realizado sin asistencia de IA
- `uso_critico_IA`: indicador de si el uso de IA fue crítico (activo, cuestionador) o dependiente
- `riqueza_de_proceso`: variedad y cantidad de eventos cognitivos (más exploraciones = mayor riqueza)

**Escala**: 0.0 a 1.0, donde:
- `0.0 - 0.3`: Proceso dependiente, principalmente N1
- `0.3 - 0.6`: Proceso en desarrollo, mezcla de niveles
- `0.6 - 0.8`: Proceso sólido, predominantemente N2-N3
- `0.8 - 1.0`: Proceso excelente, presencia significativa de N3-N4

**En el código**: Calculada por `scoring_service.compute_qe()`. Los valores se almacenan en `analytics.session_metrics`.

---

## CTR (Cognitive Trace Record)

**Definición**: Registro atómico e inmutable de un evento cognitivo significativo ocurrido durante una sesión de aprendizaje. Es la unidad fundamental del sistema de trazabilidad cognitiva.

**Estructura de un CTR**:
```json
{
  "id": "uuid",
  "session_id": "uuid",
  "user_id": "uuid",
  "event_type": "session.started | reads_problem | code.snapshot | tutor.question_asked | tutor.response_received | code.run | submission.created | reflection.submitted | session.closed",
  "content": { /* contenido variable según event_type */ },
  "cognitive_signal": "N1 | N2 | N3 | N4 | NEUTRAL",
  "ai_involvement": "none | requested | provided | critical | dependent",
  "hash": "sha256_del_contenido_y_hash_anterior",
  "previous_hash": "sha256_del_ctr_anterior | null",
  "created_at": "ISO8601_UTC"
}
```

**Inmutabilidad**: Los CTRs **nunca se modifican ni eliminan**. Esta es la diferencia más importante con el resto de las entidades del sistema que usan soft delete. La inmutabilidad es lo que hace a los CTRs confiables como evidencia académica.

**Integridad**: La cadena de hashes garantiza que no se pueden insertar, modificar, ni eliminar registros sin ser detectado.

**En el código**: Tabla `cognitive.cognitive_events`. No tiene columnas `is_active` ni `deleted_at`. El repositorio `ctr_repository.py` solo expone operaciones de creación y lectura (no update ni delete).

---

## Evento Cognitivo

**Definición**: Acción específica del estudiante que tiene significado en términos de procesamiento cognitivo. No toda interacción con el sistema es un evento cognitivo: escribir una línea de código es una acción, pero "intentar resolver el problema con un enfoque completamente diferente después de un error" es un evento cognitivo.

**Tipos de eventos cognitivos registrados (catálogo canónico)**:

| Tipo | Descripción | Señal cognitiva |
|---|---|---|
| `session.started` | Se inicia una sesión de tutor para un ejercicio | NEUTRAL |
| `reads_problem` | El alumno marca que leyó el enunciado | NEUTRAL |
| `code.snapshot` | El alumno guarda un snapshot de su código en progreso | Variable |
| `tutor.question_asked` | El alumno envía un mensaje al tutor | Variable (depende del contenido) |
| `tutor.response_received` | El tutor responde (registrado para análisis) | NEUTRAL |
| `code.run` | El alumno ejecuta su código en el sandbox | Variable |
| `submission.created` | El alumno envía código para evaluación formal | Variable (depende del resultado) |
| `reflection.submitted` | El alumno completa la reflexión post-sesión | N3-N4 |
| `session.closed` | Se cierra la sesión de tutor | NEUTRAL |

**En el código**: El campo `event_type` en el modelo `CognitiveEvent` y en el schema `CTRResponse`.

---

## Episodio Cognitivo

**Definición**: Secuencia coherente de eventos cognitivos que representan un ciclo completo de resolución de un sub-problema. Un ejercicio puede contener múltiples episodios cognitivos (p.ej. resolver el caso base de una función recursiva es un episodio; luego resolver el caso recursivo es otro).

**Distinción de sesión**: En la implementación, "episodio" mapea exactamente a `cognitive_session` — una sesión = un episodio. Los episodios son segmentos del proceso de aprendizaje que el sistema detecta automáticamente mediante análisis de los CTRs.

**En el código**: No tiene tabla propia — se detectan y calculan a partir de los CTRs. El `scoring_service.py` tiene una función `identify_episodes(ctrs: list[CognitiveEvent]) -> list[Episode]`.

---

## Uso Crítico de IA

**Definición**: Forma de interacción con la inteligencia artificial en la que el estudiante mantiene la agencia cognitiva: usa la IA como herramienta de validación, contrasta sus respuestas con razonamiento propio, y la cuestiona cuando percibe que está equivocada o es insuficiente.

**Características del uso crítico**:
- El alumno formula preguntas específicas, no genéricas.
- Evalúa la respuesta del tutor antes de aceptarla.
- Detecta cuando el tutor está evadiendo dar la respuesta y reformula la pregunta.
- Puede articular por qué una sugerencia del tutor no aplica a su situación específica.

**Contraste con uso dependiente**: Ver "Uso Dependiente de IA".

**Señal en CTRs**: Los CTRs con `ai_involvement = "critical"` contribuyen positivamente al Qe. Se detectan cuando el alumno formula preguntas de alto orden ("¿por qué este enfoque es mejor que el otro?") o cuestiona explícitamente al tutor.

---

## Uso Dependiente de IA

**Definición**: Forma de interacción con la inteligencia artificial en la que el estudiante delega la agencia cognitiva al sistema: pide soluciones directas, acepta respuestas sin procesarlas, y usa la IA como sustituto del pensamiento propio.

**Características del uso dependiente**:
- El alumno copia las sugerencias del tutor sin comprenderlas.
- Repite la misma pregunta con diferentes palabras hasta que el tutor "suelta" más información.
- No hace preguntas de comprensión, solo solicita código.
- No puede explicar el código que "escribió" si se le pregunta.

**Señal en CTRs**: Los CTRs con `ai_involvement = "dependent"` reducen el Qe. Se detectan por patrones como solicitudes repetidas de código, o respuestas del alumno que son paráfrasis literales de la respuesta del tutor sin procesamiento visible.

**Importancia**: El uso dependiente no invalida el aprendizaje, pero indica que el alumno necesita intervención pedagógica. El sistema genera alertas para el profesor cuando detecta patrones de dependencia sostenida.

---

## Métrica Cognitiva

**Definición**: Cualquier valor cuantificable derivado del análisis de CTRs que describe una dimensión del proceso de aprendizaje de un estudiante.

**Métricas implementadas**:

| Métrica | Descripción | Rango |
|---|---|---|
| `nivel_predominante` | Nivel N1-N4 más frecuente en la sesión | N1 / N2 / N3 / N4 |
| `distribucion_niveles` | % de eventos en cada nivel N1-N4 | 0-100% por nivel |
| `calidad_epistemica` (Qe) | Métrica compuesta de calidad del proceso | 0.0 - 1.0 |
| `autonomia_ratio` | % de proceso sin asistencia de IA | 0.0 - 1.0 |
| `ai_uso_critico_ratio` | % de interacciones con IA de tipo "crítico" | 0.0 - 1.0 |
| `intentos_por_ejercicio` | Número de code submissions antes de resolver | Integer |
| `duracion_sesion_minutos` | Tiempo total de la sesión | Integer |
| `eventos_por_minuto` | Densidad de actividad cognitiva | Float |

**En el código**: Calculadas por `scoring_service.py` y almacenadas en `analytics.session_metrics`.

---

## Evidencia Procesual

**Definición**: Registro del camino seguido por el estudiante durante la resolución de un problema, en contraste con la evidencia de resultado (el código final). La evidencia procesual incluye los errores cometidos, las preguntas realizadas, los enfoques descartados, y el uso de herramientas de asistencia.

**Importancia en la evaluación**: La evidencia procesual permite distinguir entre un alumno que llegó a la solución correcta por comprensión genuina y uno que la obtuvo por imitación o asistencia excesiva. Un estudiante que llegó a la solución incorrecta pero mostró un proceso rico de exploración puede tener mayor valor cognitivo que uno que la "acertó" sin proceso visible.

**En el código**: Es la suma de todos los CTRs de una sesión. El sistema de trazabilidad cognitiva está diseñado para maximizar la captura de evidencia procesual.

---

## Tutor Socrático

**Definición**: Agente de inteligencia artificial que asiste al estudiante mediante el método socrático: en lugar de proporcionar respuestas directas, formula preguntas que guían al estudiante hacia el descubrimiento autónomo de la solución.

**Principios del método socrático en este contexto**:
1. No proporcionar código funcional directamente.
2. Responder preguntas con preguntas cuando el alumno está cerca de una comprensión.
3. Señalar contradicciones o inconsistencias en el razonamiento del alumno.
4. Validar el proceso correcto independientemente del resultado.
5. Ajustar el nivel de las preguntas al nivel cognitivo detectado del alumno.

**Implementación técnica**: El tutor es un sistema basado en Claude (Anthropic) con un prompt base socrático que incluye el contexto del ejercicio, el historial de la sesión, y las guías de comportamiento (guardrails anti-solver).

**En el código**: `tutor_service.py`, `integrations/anthropic/client.py`, `integrations/anthropic/prompt_builder.py`.

---

## Guardrails Anti-Solver

**Definición**: Sistema de restricciones técnicas que previenen que el tutor socrático proporcione soluciones directas al estudiante, independientemente de cómo formule la pregunta.

**Capas de los guardrails**:

1. **Prompt base**: Las instrucciones del sistema le dicen explícitamente al LLM que no puede proporcionar código funcional completo.

2. **Pre-procesamiento de input**: Antes de enviar el mensaje del alumno al LLM, se detectan intenciones de solicitar solución. Si se detecta una intención de alta confianza, se transforma el mensaje para que el LLM reciba una versión reformulada.

3. **Post-procesamiento de output**: Antes de enviar la respuesta del LLM al estudiante, se analiza si contiene código de solución. Si lo contiene, se reemplaza por una respuesta de fallback socrática.

4. **Tests adversariales**: Suite de 20+ prompts diseñados para bypassear los guardrails. Se ejecutan regularmente para verificar que el sistema es robusto.

**En el código**: `integrations/anthropic/guardrails.py`. Los tests están en `tests/adversarial/test_tutor_guardrails.py`.

---

## Hash Chain

**Definición**: Estructura de datos criptográfica donde cada registro contiene un hash del registro anterior, formando una cadena que hace imposible modificar cualquier registro sin invalidar todos los registros posteriores.

**Funcionamiento**:
```
CTR_1: hash = SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())
CTR_2: hash = SHA256(content_2 + hash_CTR_1)
CTR_3: hash = SHA256(content_3 + hash_CTR_2)
...
CTR_N: hash = SHA256(content_N + hash_CTR_(N-1))
```

Si se modifica el contenido de `CTR_2`, su hash cambia, lo que hace que el hash de `CTR_3` ya no coincida con lo esperado, y así hasta el final de la cadena.

**Propósito**: Garantizar que los CTRs son evidencia confiable e inmutable del proceso de aprendizaje. Nadie (ni los administradores del sistema) puede modificar el historial sin que sea detectable.

**Requisito de determinismo**: La serialización del contenido para el cálculo del hash debe ser determinista. Se usa `json.dumps(content, sort_keys=True)` para garantizar que el mismo objeto Python siempre produce el mismo JSON string.

**En el código**: `app/core/hash_chain.py`. La tabla `cognitive.cognitive_events` tiene las columnas `hash` y `previous_hash`. El `ctr_service.py` calcula el hash antes de cada inserción.

---

## Principio de Subordinación Técnica

**Definición**: Principio pedagógico central del sistema que establece que la inteligencia artificial debe estar subordinada al proceso de aprendizaje humano, no al revés. La IA es una herramienta al servicio del desarrollo cognitivo del estudiante, no un sustituto del esfuerzo intelectual.

**Implicaciones en el diseño del sistema**:
1. El tutor no puede dar soluciones aunque el alumno lo pida insistentemente.
2. El sistema mide y valora la autonomía cognitiva más que la velocidad de resolución.
3. El uso de IA se registra explícitamente para hacer visible la dependencia.
4. Los algoritmos de evaluación penalizan la dependencia excesiva en la métrica Qe.

**Tensión con usabilidad**: Este principio puede frustrar a alumnos que están acostumbrados a buscar soluciones directas en internet. La introducción gradual al sistema requiere acompañamiento pedagógico.

---

## Principio de No Degradación Semántica

**Definición**: Principio que establece que el sistema de trazabilidad cognitiva no debe degradar, simplificar, ni reinterpretar los eventos cognitivos del estudiante al registrarlos. Los CTRs deben preservar la semántica original de la interacción.

**Implicaciones en el diseño**:
1. El contenido de los CTRs se almacena como JSONB sin transformaciones de esquema fijo.
2. Los mensajes del alumno y del tutor se guardan completos, no resumidos.
3. Los metadatos de contexto (ejercicio, timestamp, session state) se preservan en cada CTR.
4. La clasificación N1-N4 es una interpretación del evento, no el evento en sí.

**Separación entre datos y análisis**: Los CTRs son datos crudos. Los niveles N1-N4, las métricas Qe, y otras clasificaciones son análisis que se calculan a partir de los datos. Si el algoritmo de análisis mejora, se puede recalcular sobre los datos crudos originales sin perder información.

**En el código**: El campo `content` del CTR es JSONB sin esquema fijo. El campo `cognitive_signal` (N1-N4) es una clasificación calculada en el momento de creación, pero los datos originales siempre están disponibles para reclasificación.
