## Why

Los ejercicios son el punto de contacto principal alumno-plataforma. Sin ellos no hay código que ejecutar, submissions que enviar, ni tutor que contextualizar. EPIC-05 dejó cursos y comisiones; ahora montamos ejercicios sobre esa estructura. Además, al abrir un ejercicio se emite `reads_problem` — el primer dato cognitivo del alumno (N1).

## What Changes

### Backend
- Modelo `Exercise` con JSONB test_cases, TEXT[] topic_tags, difficulty ENUM, starter_code, metadata
- Migración Alembic 004 con índice GIN sobre topic_tags
- ExerciseRepository con filtros avanzados (dificultad, topic, búsqueda)
- ExerciseService con validación de test_cases schema
- Endpoints REST: CRUD ejercicios (docente), listado+detalle (alumno)
- Emisión evento `reads_problem` al Event Bus cuando alumno abre detalle

### Frontend
- Docente: ABM ejercicios (enunciado, test cases, starter code, metadata)
- Alumno: listado con filtros + vista detalle del enunciado
- Seed data con 3 ejercicios de ejemplo

## Capabilities

### New Capabilities
- `exercise-model`: Modelo Exercise con JSONB test_cases, TEXT[] topic_tags, difficulty ENUM, GIN index
- `exercises-api`: CRUD endpoints + student listing + reads_problem event emission
- `exercises-frontend`: ABM docente + listado/detalle alumno con filtros

### Modified Capabilities
- `monorepo-structure`: Se agrega features/exercises backend y frontend

## Impact

- **Backend**: `backend/app/features/exercises/`, `backend/app/shared/models/exercise.py`, migración 004
- **Frontend**: `frontend/src/features/exercises/`
- **Database**: Tabla `exercises` en schema operational con GIN index
- **Event Bus**: Evento `reads_problem` en stream `events:submissions`
- **Downstream**: Desbloquea EPIC-07 (sandbox), EPIC-08 (submissions), EPIC-09 (tutor)
