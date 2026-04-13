# EPIC-10: Prompt Engine y Guardrails Anti-Solver

> **Issue**: #10 | **Milestone**: Fase 2 — Tutor IA | **Labels**: epic, fase-2, priority:critical

**Nivel de gobernanza**: CRITICAL — cambios requieren revisión formal

## Contexto

El tutor NUNCA debe entregar soluciones completas. Máximo 5 líneas de código parcial y contextual. Este EPIC implementa el constructor de contexto (arma el prompt completo) y los guardrails que analizan cada respuesta del LLM ANTES de enviarla al alumno. Si detecta una solución directa, la reformula.

Esto es lo que diferencia a esta plataforma de ChatGPT. Si los guardrails fallan, el modelo teórico doctoral se invalida.

**Relación con EPIC-09**: EPIC-09 entrega un chat funcional con un system prompt básico hardcodeado. Este EPIC reemplaza ese placeholder con el `ContextBuilder` completo (que incorpora ejercicio + código actual + historial de conversación + constraints del ejercicio) y agrega el `GuardrailsProcessor` como paso de post-procesamiento ANTES de enviar cada respuesta al alumno.

## Alcance

### Backend
- **Constructor de contexto** (pre-procesador):
  - Reemplaza el system prompt básico de EPIC-09
  - Arma prompt completo: system prompt socrático + enunciado del ejercicio + código actual + historial de chat + restricciones
  - Normaliza input del alumno
  - Detecta idioma
  - Inyecta metadata del ejercicio (dificultad, topics)
- **Post-procesador / Guardrails**:
  - Analiza respuesta del LLM antes de enviar al alumno
  - Detecta soluciones directas (código completo, respuestas que resuelven el ejercicio)
  - Reformula: convierte solución en pregunta socrática
  - Las violaciones de guardrails se registran como `governance_events` (NO como campo en `tutor_interactions` — ese campo no existe)
  - La clasificación N4 del turno se persiste como `n4_level` en `tutor_interactions`
  - Configurable via `guardrails_config` en `tutor_system_prompts`
- **System prompt socrático v1**: basado en Anexo A del documento maestro
- **Versionado de prompts**: cada prompt tiene SHA-256, cada interacción referencia el hash

### Frontend
- Indicador visual si el tutor reformuló una respuesta (sutil, para debugging/governance)
- Sin UI compleja propia — los guardrails son transparentes para el alumno

## Contratos

### Produce
- `ContextBuilder` service reutilizable
- `GuardrailsProcessor` service
- System prompt socrático versionado con SHA-256
- `governance_events` con tipo `policy_violation` cuando un guardrail interviene (se registra en EPIC-11, este EPIC produce los datos)
- Evento: `guardrail.triggered` (exercise_id, student_id, violation_type, original_response_snippet) — para Event Bus

### Consume
- Chat streaming (de EPIC-09)
- Ejercicios con enunciado y constraints (de EPIC-06)
- Código actual del alumno (de EPIC-08)
- System prompts versionados (modelo `governance.tutor_system_prompts` de EPIC-09)

### Modelos
- No crea modelos nuevos. Usa `governance.tutor_system_prompts` (EPIC-09) y `governance.governance_events` (EPIC-11).
- **No existe** un campo `policy_check_result` en `tutor_interactions`. Las violaciones se persisten en `governance_events` via `GovernanceService`.

## Dependencias
- **Blocked by**: EPIC-09 (necesita el chat streaming funcionando)
- **Blocks**: EPIC-11 (governance events registran violaciones de guardrails)

## Stories

- [ ] System prompt socrático v1 (basado en Anexo A del documento maestro)
- [ ] ContextBuilder: arma prompt completo (system + ejercicio + código + historial + restricciones)
- [ ] GuardrailsProcessor: detectar soluciones directas en respuesta del LLM
- [ ] GuardrailsProcessor: reformular solución → pregunta socrática
- [ ] Integrar ContextBuilder + GuardrailsProcessor en el flujo WebSocket de EPIC-09
- [ ] Versionado de prompts con SHA-256 (hash en cada interacción)
- [ ] Producir datos de violación para que GovernanceService registre `governance_events`
- [ ] Producir evento `guardrail.triggered` para Event Bus
- [ ] Frontend: indicador sutil de reformulación
- [ ] 20+ tests adversarios: intentos de extraer solución, jailbreak, bypass
- [ ] Tests: constructor de contexto con distintos estados del alumno

## Criterio de Done

- El tutor NUNCA entrega soluciones completas (verificado por 20+ tests adversarios)
- Cada respuesta pasa por guardrails antes de llegar al alumno
- Reformulaciones son naturales (no se nota que se bloqueó algo)
- Cada interacción tiene prompt_hash del system prompt vigente
- Violaciones de guardrails se registran como `governance_events` con tipo `policy_violation`
- NO existe campo `policy_check_result` en `tutor_interactions`
- TODOS los tests adversarios pasan

## Referencia
- `prompts/socratic_tutor_system.md`
- `knowledge-base/01-negocio/04_reglas_de_negocio.md` (reglas del tutor)
- `knowledge-base/03-seguridad/02_superficie_de_ataque.md`
