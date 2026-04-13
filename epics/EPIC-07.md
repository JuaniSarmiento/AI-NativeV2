# EPIC-07: Sandbox de Ejecución Segura

> **Issue**: #7 | **Milestone**: Fase 1 — Core Académico | **Labels**: epic, fase-1, priority:critical

## Contexto

El sandbox ejecuta código Python de los alumnos de forma segura y aislada. Es una pieza CRÍTICA de seguridad — código arbitrario de usuarios corre en el servidor. Restricciones: timeout 10s, 128MB RAM, sin acceso a red, sin filesystem fuera de /tmp.

## Alcance

### Backend
- Sandbox engine: subprocess con límites de CPU/memoria/tiempo
- Test runner: ejecuta assertions individuales contra el código del alumno
- Endpoint: `POST /api/v1/student/exercises/{id}/run` → `{ stdout, stderr, runtime_ms, test_results, status }`
- Manejo de edge cases: timeout, memory exceeded, syntax error, runtime error, infinite loop
- Emisión de eventos al Event Bus para cada ejecución (éxito y fallo)
- Logging de cada ejecución (para auditoría)

### Frontend
- Panel de output en la vista de ejercicio:
  - Botón "Ejecutar" con loading state
  - Visualización de stdout/stderr
  - Resultados de test cases (pass/fail individual con feedback)
  - Indicadores de runtime_ms y status
- Feedback visual según estado: success (verde), error (rojo), timeout (amarillo)

## Contratos

### Produce
- `POST /api/v1/student/exercises/{id}/run` → resultado de ejecución
- `SandboxService` reutilizable por EPIC-08 (submission flow)
- Evento `code.executed` (stream: `events:code`) — emitido en cada ejecución exitosa. Payload: `{ student_id, exercise_id, session_id, code, language, stdout, stderr, exit_code, execution_time_ms, test_results, timestamp }`
- Evento `code.execution.failed` (stream: `events:code`) — emitido cuando la ejecución falla (timeout, memory, syntax error, runtime error). Payload: `{ student_id, exercise_id, session_id, code, language, error_type, stderr, execution_time_ms, timestamp }`

### Consume
- Ejercicios con test_cases (de EPIC-06)
- Auth (de EPIC-03)

### Modelos
- No crea modelos nuevos (los resultados se persisten en submissions, EPIC-08)

## Dependencias
- **Blocked by**: EPIC-06 (necesita ejercicios con test_cases)
- **Blocks**: EPIC-08 (submission flow usa el sandbox)

## Stories

- [ ] Sandbox engine: subprocess con timeout 10s, memory 128MB, sin red, sin filesystem
- [ ] Test runner: ejecutar assertions individuales, reporte pass/fail por caso
- [ ] Endpoint `POST /api/v1/student/exercises/{id}/run`
- [ ] Manejo de edge cases: timeout, memory, syntax error, runtime error, infinite loop
- [ ] Emisión del evento `code.executed` al Event Bus tras ejecución exitosa
- [ ] Emisión del evento `code.execution.failed` al Event Bus tras ejecución fallida
- [ ] Frontend: botón ejecutar con loading state
- [ ] Frontend: panel de output (stdout, stderr, test results)
- [ ] Frontend: feedback visual por estado (verde/rojo/amarillo)
- [ ] Tests de integración: ejecución correcta, timeout, memory limit, syntax error, código malicioso

## Criterio de Done

- Código Python se ejecuta con límites de seguridad estrictos
- Test cases corren individualmente con reporte pass/fail
- Edge cases manejados sin crash del servidor
- UI muestra resultados claramente
- Código malicioso (import os, socket, etc.) bloqueado
- Eventos `code.executed` y `code.execution.failed` se emiten correctamente al Event Bus
- Tests de integración pasan incluyendo tests adversarios de seguridad

## Referencia
- `knowledge-base/02-arquitectura/04_patrones_de_diseno.md` (sandbox)
- `knowledge-base/03-seguridad/02_superficie_de_ataque.md`
