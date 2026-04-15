## Why

El alumno puede ejecutar código pero no puede enviarlo. Sin submissions no hay registro de lo que el alumno entregó, no hay snapshots del proceso de escritura, y el docente no puede ver el trabajo. Esta EPIC cierra el flujo: escribir → ejecutar → iterar → enviar actividad completa. Los snapshots son evidencia inmutable del proceso cognitivo.

## What Changes

### Backend
- Modelos: `submissions` (por ejercicio), `code_snapshots` (inmutables), `activity_submissions` (agrupador por actividad)
- Migración Alembic 008
- SubmissionService: crear submission por ejercicio al enviar actividad, registrar attempt_number
- SnapshotService: guardar snapshot (inmutable, sin UPDATE/DELETE)
- Endpoints: enviar actividad, mis submissions, detalle, snapshots
- Eventos: `exercise.submitted`, `code.snapshot.captured`

### Frontend
- Auto-snapshot cada 30s + ante ejecución
- Botón "Enviar actividad" (confirma, crea submissions para todos los ejercicios)
- Historial de envíos del alumno
- Docente: ver submissions de alumnos

## Capabilities

### New Capabilities
- `submission-model`: Modelos Submission, CodeSnapshot, ActivitySubmission con migración
- `submission-api`: Endpoints para enviar actividad, listar submissions, guardar snapshots
- `submission-frontend`: Auto-snapshot, botón enviar, historial

### Modified Capabilities
- `monorepo-structure`: Se agregan features/submissions backend y frontend

## Impact

- **Backend**: `backend/app/features/submissions/`
- **Frontend**: Modificación de StudentActivityViewPage + nueva página de historial
- **Database**: Tablas submissions, code_snapshots, activity_submissions en operational
- **Event Bus**: Eventos exercise.submitted, code.snapshot.captured
