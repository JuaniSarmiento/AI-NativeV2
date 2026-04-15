## Why

Las actividades generadas por IA tienen ejercicios con test cases evaluables (stdin/stdout). Pero el alumno no puede ejecutar código todavía. Sin sandbox, las actividades son solo lectura. Esta EPIC cierra el loop: el alumno escribe código → lo ejecuta → ve resultados → los test cases se evalúan automáticamente.

## What Changes

### Backend
- Sandbox engine: subprocess aislado con timeout 10s, 128MB RAM, sin red, sin filesystem
- Test runner: ejecuta cada test case individualmente contra el código del alumno
- Endpoint `POST /api/v1/student/exercises/{id}/run` con código como body
- Manejo de edge cases: timeout, memory exceeded, syntax error, runtime error, infinite loops
- Eventos `code.executed` y `code.execution.failed` al Event Bus
- Bloqueo de imports peligrosos (os, subprocess, socket, etc.)

### Frontend
- Editor de código dentro de la vista de actividad del alumno
- Botón "Ejecutar" con loading state
- Panel de output: stdout, stderr, test results (pass/fail individual)
- Feedback visual: verde (pass), rojo (error), amarillo (timeout)

## Capabilities

### New Capabilities
- `sandbox-engine`: Ejecución segura de código Python con subprocess aislado
- `sandbox-api`: Endpoint de ejecución + test runner con resultados individuales
- `sandbox-frontend`: Editor de código + panel de output + resultados de tests

### Modified Capabilities
- `monorepo-structure`: Se agrega features/sandbox backend, se modifica vista de actividad del alumno

## Impact

- **Backend**: `backend/app/features/sandbox/`
- **Frontend**: Modificación de `StudentActivityViewPage` para agregar editor + output
- **Event Bus**: Eventos `code.executed` y `code.execution.failed` en stream `events:code`
- **Seguridad**: Ejecución de código arbitrario — sandbox CRÍTICO
