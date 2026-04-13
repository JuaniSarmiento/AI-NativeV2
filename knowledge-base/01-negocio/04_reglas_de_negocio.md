# Reglas de Negocio

## Reglas Normativas del Dominio AI-Native

Estas reglas se derivan del Documento Maestro de Unificación Conceptual (empate3) y del modelo teórico N4 de la tesis doctoral. Son **no negociables** — violarlas rompe la coherencia del modelo.

### RN-1: No hay evaluación sin trazabilidad

Toda evaluación debe estar respaldada por evidencia en el CTR. No se puede emitir un score N1-N4 sin que existan eventos cognitivos clasificados que lo sustenten.

- **Enforcement**: Evaluation Engine valida existencia de eventos antes de computar métricas
- **Violación**: Emitir score basado solo en `submissions.score` sin CTR
- **Impacto**: Regresa al modelo `E = correctness(output)` que el sistema reemplaza

### RN-2: No hay métrica sin interpretación

Toda métrica debe tener significado pedagógico explícito. Un número sin contexto no es una métrica del modelo N4.

- **Enforcement**: Cada métrica en `cognitive_metrics` tiene documentación de su significado en la rúbrica N4
- **Violación**: Agregar un campo `total_events_count` sin explicar qué mide pedagógicamente
- **Impacto**: Acumulación de datos sin valor interpretativo — contra principio de trazabilidad semántica

### RN-3: No hay dato sin contexto

Todo evento cognitivo debe incluir: tiempo, contexto del problema, estado del estudiante.

- **Enforcement**: Schema de `cognitive_events` requiere `timestamp`, `session_id` (vincula a ejercicio y estudiante), `payload` con contexto
- **Violación**: Registrar un evento como log genérico sin contexto pedagógico
- **Impacto**: El CTR pierde capacidad de reconstrucción del proceso

### RN-4: No hay IA sin registro

Toda interacción con IA debe registrarse completamente: prompt, respuesta, clasificación N4.

- **Enforcement**: `tutor_interactions` registra student_message, tutor_response, classification_n4, model_version, y el campo `prompt_hash` (VARCHAR 64) con el SHA-256 del system prompt vigente al momento de cada interacción
- **Violación**: Llamar al LLM sin persistir la interacción
- **Impacto**: Se pierde evidencia de N4 — el CTR queda incompleto

### RN-5: No hay evaluación binaria

La evaluación debe ser multidimensional: técnica, cognitiva, metacognitiva, uso de IA.

- **Enforcement**: Evaluation Engine siempre produce 4 scores (N1-N4) + Qe + dependency, nunca un solo número
- **Violación**: Reportar al docente solo `score: 7.5` sin desglose dimensional
- **Impacto**: Vuelve al paradigma de evaluación por producto que el sistema reemplaza

### RN-6: El tutor nunca entrega soluciones completas

El tutor IA es un mediador socrático. Máximo 5 líneas de código por bloque, siempre parcial y contextual.

- **Enforcement**: Post-procesador / guardrails inspecciona cada respuesta del LLM antes de enviar al alumno. Detecta bloques de código > 5 líneas, soluciones completas, afirmaciones imperativas sobre "el código correcto"
- **Violación detectada**: Se reformula automáticamente y se registra `governance_event` con `event_type: policy_violation`
- **Impacto**: Si el tutor da respuestas, el alumno no genera evidencia de razonamiento propio → el CTR pierde validez

### RN-7: El CTR es inmutable post-cierre

Una vez cerrada la sesión cognitiva, el CTR no se modifica. La integridad se garantiza por hash chain.

- **Enforcement**: hash génesis `SHA256("GENESIS:" + session_id + ":" + started_at.isoformat())`, encadenado con `hash(n) = SHA256(hash(n-1) + datos(n))`. `ctr_hash_chain` almacena el hash final. `is_valid_ctr` se computa al cierre
- **Violación**: Modificar un evento cognitivo después del cierre de sesión
- **Impacto**: Se rompe la cadena de hashes — la traza deja de ser auditable

### RN-8: Propiedad de datos por fase

Solo la fase dueña de un schema puede INSERT/UPDATE/DELETE en sus tablas. Las otras fases leen via endpoints REST.

- **Enforcement**: Permisos de DB + contratos de API
- **Violación**: Fase 4 (frontend) haciendo INSERT directo en `cognitive_events`
- **Impacto**: Acoplamientos ocultos que impiden evolución independiente de fases

## Reglas Operativas

### RO-1: CTR mínimo viable

Un CTR es válido (`is_valid_ctr = true`) si contiene al menos 1 evento interpretable por cada nivel N1-N4 por episodio.

- **Enforcement**: CTR Builder valida al cierre de sesión
- **Si no se cumple**: `is_valid_ctr = false`. El CTR existe pero no puede sostener conclusiones evaluativas formales

### RO-2: Rate limiting del tutor

30 mensajes/hora por alumno por ejercicio. Previene spam al LLM y uso excesivo de cuota de Anthropic.

- **Enforcement**: Rate limiter en endpoint de chat / WebSocket
- **Si se excede**: HTTP 429 con mensaje indicando tiempo de espera

### RO-3: Sandbox de ejecución

Código del alumno ejecutado con: timeout 10s, memory limit 128MB, sin acceso a red, sin acceso a filesystem fuera de /tmp.

- **Enforcement**: subprocess con restricciones (dev), Docker con seccomp profile (prod)
- **Si se excede**: Proceso terminado, resultado con stderr indicando el límite alcanzado

### RO-4: Versionado de prompts del tutor

Cada versión del system prompt tiene: semver, texto completo, campo `sha256_hash` (VARCHAR 64, SHA-256 del `prompt_text` para verificación de integridad), flag active, notas de cambio.

- **Enforcement**: `tutor_system_prompts` table con campo `sha256_hash`. Cada interacción registra el hash del prompt vigente en el campo `prompt_hash` de `tutor_interactions`
- **Cambio de prompt**: Genera governance event. Requiere role admin. Pruebas de conformidad pedagógica antes de activar

### RO-5: Reflexión post-ejercicio obligatoria

Al finalizar (enviar submission), el alumno debe completar un formulario de reflexión guiada.

- **Enforcement**: UI muestra formulario automáticamente post-submission. Los datos alimentan el CTR como evento de metacognición
- **Si se omite**: La submission se acepta pero el CTR queda sin evento de metacognición (afecta reflection_score)

### RO-6: Snapshots automáticos de código

El código del alumno se guarda automáticamente cada 30 segundos y ante cada ejecución.

- **Enforcement**: Frontend emite `POST /code_snapshots` periódicamente. Backend registra snapshots; la distancia de edición se calcula on-the-fly cuando se necesita para análisis de evolución
- **Impacto**: Permite reconstruir la evolución del código como parte del CTR

## Reglas de Gobernanza (empate3)

### RG-1: Principio de subordinación técnica

La arquitectura depende del modelo pedagógico. Nunca al revés. Ningún endpoint existe sin justificación en el constructo teórico.

### RG-2: Principio de no degradación semántica

Un evento cognitivo no puede ser reducido a log técnico sin pérdida semántica. La persistencia debe conservar contexto, fuente, intención y clasificación.

- **Anti-ejemplo**: ❌ "eventos" como logs genéricos
- **Correcto**: ✅ eventos como representaciones cognitivas con clasificación N4

### RG-3: Principio de coherencia evaluativa

La evaluación final no puede derivarse únicamente de `submissions.score`. Debe integrar evidencia técnica, cognitiva y de interacción con IA.

### RG-4: Versionado semántico del documento maestro

- **Cambio mayor (X.0)**: modifica constructo estable (ej: niveles N1-N4) → revisión formal conjunta con manuscrito doctoral
- **Cambio menor (X.Y)**: modifica constructo operativo provisional (ej: umbrales CTR, mapeo event_type → N4) → aprobación del responsable institucional
- **Cambio de refinamiento (X.Y.Z)**: ajusta constructo en refinamiento (ej: dependency score, calidad epistémica) → fundamentación escrita

### RG-5: Auditor de coherencia AI-Native

Rol institucional que verifica periódicamente:
1. Vocabulario canónico no haya derivado entre documentos y código
2. Estado de excepciones justificadas
3. Historial de versionado semántico del documento maestro
4. Desacoples entre constructo teórico y componente técnico

## Matriz de Validación de Coherencia

Toda decisión técnica puede auditarse con 5 preguntas:

1. ¿Qué constructo de la tesis justifica este componente?
2. ¿Qué evidencia produce o consume?
3. ¿En qué tabla queda persistida?
4. ¿Qué endpoint habilita su operación?
5. ¿Cómo impacta en la evaluación?

Si cualquiera no puede responderse con precisión, **existe una brecha de alineación**.
