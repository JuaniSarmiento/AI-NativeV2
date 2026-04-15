## Context

El TutorService (EPIC-09) tiene un flujo funcional de chat streaming via WebSocket. El LLM recibe un system prompt generico sin contexto del ejercicio ni del alumno. No hay post-procesamiento — cualquier respuesta del LLM se envia directamente. Esto hace que el tutor no pueda dar feedback contextualizado y no hay garantia de que no entregue soluciones completas.

Estado actual del pipeline:
```
mensaje alumno → rate limit → prompt raw → LLM stream → persist → outbox
```

Estado objetivo:
```
mensaje alumno → rate limit → ContextBuilder(ejercicio + rubrica + codigo + historial) → LLM stream → GuardrailsProcessor → persist → outbox
```

Modelos disponibles para consumir:
- `Exercise`: description, difficulty, topic_tags, rubric, starter_code, language
- `CodeSnapshot`: ultimo codigo del alumno (student_id + exercise_id, ordenado por snapshot_at DESC)
- `TutorSystemPrompt`: prompt activo con guardrails_config JSONB
- `TutorInteraction`: historial de la sesion (ya cargado por el service)

## Goals / Non-Goals

**Goals:**
- ContextBuilder compone prompt completo con contexto del ejercicio (enunciado, rubrica, dificultad, topics) y codigo actual del alumno
- GuardrailsProcessor analiza respuesta completa del LLM y detecta violaciones (codigo excesivo, soluciones directas)
- Reformulacion automatica cuando se detecta violacion — no se bloquea, se reformula
- Evento `guardrail.triggered` para auditoria (governance)
- System prompt v2 con template de contexto dinamico
- 20+ tests adversarios validando que el tutor no entrega soluciones

**Non-Goals:**
- Clasificacion N4 de interacciones (EPIC-11)
- Governance events persistence en tabla governance_events (EPIC-11)
- UI changes en el frontend — el protocolo WS no cambia
- Cache de ejercicios o snapshots — optimizacion prematura
- Evaluacion de calidad de la respuesta pedagogica — solo deteccion de violaciones

## Decisions

### D1: ContextBuilder como servicio stateless inyectado en TutorService

El ContextBuilder recibe exercise_id y student_id, consulta Exercise y CodeSnapshot via repositorios, y retorna el system prompt compuesto como string.

**Alternativa considerada**: Decorator pattern sobre LLMAdapter. Descartado porque el contexto requiere queries a DB que no pertenecen a la capa de LLM.

**Alternativa considerada**: Middleware en el router. Descartado porque el contexto es logica de dominio, no HTTP concern.

### D2: GuardrailsProcessor opera sobre respuesta completa post-stream, no por token

El streaming al frontend sigue funcionando igual. Despues de acumular la respuesta completa, GuardrailsProcessor la analiza. Si hay violacion, se persiste la respuesta original con flag `guardrail_triggered=true`, se reformula, y se envia un mensaje adicional de correccion.

**Razon**: Analizar por token es fragil (no se puede detectar "solucion completa" en un token parcial) y rompe la UX de streaming.

**Flujo si hay violacion**:
1. Stream llega completo al frontend (UX no se interrumpe)
2. GuardrailsProcessor detecta violacion en el texto acumulado
3. Se persiste la interaccion original con metadata de violacion
4. Se emite evento `guardrail.triggered` al outbox
5. Se envia un mensaje de seguimiento corrigiendo/reformulando via WS

**Alternativa considerada**: Bloquear respuesta y re-generar. Descartado porque duplica latencia y costo de tokens.

### D3: Deteccion de violaciones basada en heuristicas, no en LLM secundario

Reglas de deteccion:
1. **Codigo excesivo**: >5 lineas de codigo en bloques ``` (regex)
2. **Solucion completa**: respuesta contiene funcion/clase completa que resuelve el ejercicio (pattern matching con keywords + estructura)
3. **Respuesta directa sin proceso**: respuesta da la respuesta sin preguntas socraticas (heuristica: no contiene signos de interrogacion ni frases de guia)

**Razon**: Un LLM secundario agrega latencia, costo, y complejidad. Las heuristicas cubren el 90% de los casos y son deterministas (testeables). En la v2 se puede agregar clasificacion LLM.

### D4: System prompt v2 con template Jinja-like usando format strings

El prompt base tiene placeholders `{exercise_title}`, `{exercise_description}`, `{exercise_rubric}`, `{student_code}`, etc. ContextBuilder los reemplaza con str.format().

**Razon**: Simple, sin dependencias. El prompt se versiona en `seed.py` con SHA-256 como hasta ahora.

### D5: CodeSnapshot se consulta con query directo, sin pasar por submission

Query: ultimo CodeSnapshot por (student_id, exercise_id) ordenado por snapshot_at DESC LIMIT 1. Si no hay snapshot, se usa starter_code del ejercicio.

### D6: Nuevo schema WS para mensaje de correccion post-guardrail

Se agrega un nuevo tipo de mensaje WS `chat.guardrail` que el frontend puede renderizar con estilo diferenciado (ej: borde amarillo). El frontend existente ignora tipos desconocidos gracefully.

## Risks / Trade-offs

- **[Heuristicas imperfectas]** → Las reglas regex pueden tener falsos positivos/negativos. Mitigacion: tests adversarios extensivos + config en guardrails_config JSONB para ajustar thresholds sin redeploy.
- **[Respuesta ya enviada al stream]** → Si el guardrail detecta violacion, el alumno ya vio la respuesta. Mitigacion: mensaje de correccion inmediato post-stream. En futuras versiones se puede implementar buffering pre-send.
- **[Performance de queries adicionales]** → ContextBuilder agrega 2 queries (Exercise + CodeSnapshot) por mensaje. Mitigacion: ambos queries usan indices existentes (exercise_id PK, student_id+exercise_id index en snapshots). Latencia esperada <5ms cada uno.
- **[Prompt size]** → Con ejercicio largo + codigo largo + historial, el prompt puede crecer. Mitigacion: truncar historial a ultimos 10 mensajes (en vez de 20), truncar codigo a ultimos 2000 chars.
