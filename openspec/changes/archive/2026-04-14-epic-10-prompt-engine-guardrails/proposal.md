## Why

El TutorService actual llama al LLM con el system prompt raw, sin contexto del ejercicio (enunciado, dificultad, rubrica, topics), sin el codigo actual del alumno, y sin post-procesamiento de guardrails. Esto significa que el tutor no puede dar respuestas contextualizadas al problema que el alumno esta resolviendo, y no hay proteccion contra respuestas que entreguen soluciones completas. EPIC-10 cierra esa brecha critica antes de que el sistema sea usable con alumnos reales.

## What Changes

- Nuevo `ContextBuilder` service que arma el prompt completo con: system prompt base + enunciado del ejercicio + rubrica + dificultad/topics + codigo actual del alumno (ultimo snapshot) + constraints pedagogicos
- Nuevo `GuardrailsProcessor` service que analiza cada respuesta del LLM antes de enviarla al alumno: detecta soluciones completas, codigo excesivo (>5 lineas), respuestas no pedagogicas, y reformula si hay violacion
- Nuevo system prompt socratico v2 con placeholders para contexto dinamico (ejercicio, codigo, restricciones)
- Integracion de ambos servicios en `TutorService.chat()`: ContextBuilder antes del LLM, GuardrailsProcessor despues del stream
- Evento `guardrail.triggered` emitido al outbox cuando se detecta una violacion
- Tests adversarios (20+) para validar que el tutor no entrega soluciones

## Capabilities

### New Capabilities
- `tutor-context-builder`: Servicio que construye el prompt completo con contexto del ejercicio (enunciado, rubrica, dificultad, topics, starter_code), codigo actual del alumno (ultimo CodeSnapshot), y constraints pedagogicos. Compone el system prompt final que se envia al LLM.
- `tutor-guardrails`: Post-procesador que analiza respuestas del LLM antes de enviarlas. Detecta codigo excesivo (>5 lineas), soluciones completas, respuestas directas sin pedagogia. Reformula violaciones y emite evento `guardrail.triggered` al outbox.
- `tutor-prompt-v2`: System prompt socratico v2 con template de contexto dinamico. Incluye secciones para ejercicio, rubrica, codigo del alumno, y reglas de guardrails embebidas.

### Modified Capabilities
- `tutor-chat-ws`: El flujo de chat se modifica para integrar ContextBuilder (pre-LLM) y GuardrailsProcessor (post-LLM) en el pipeline de streaming.

## Impact

- **Backend**: `app/features/tutor/` — nuevos archivos `context_builder.py`, `guardrails.py`; modificaciones a `service.py` y `seed.py`
- **Models consumidos**: Exercise (rubric, description, difficulty, topic_tags, starter_code), CodeSnapshot (ultimo codigo), TutorSystemPrompt (prompt activo + guardrails_config), TutorInteraction (historial)
- **Repositories**: Nuevo query para obtener ultimo CodeSnapshot por student+exercise
- **Eventos**: Nuevo `guardrail.triggered` en outbox, routeado a `events:tutor` stream
- **Frontend**: Sin cambios — el chat UI ya existe y el streaming sigue el mismo protocolo WS
- **Dependencias**: Sin nuevas dependencias de paquetes
