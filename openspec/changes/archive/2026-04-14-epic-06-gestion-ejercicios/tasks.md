## 1. Exercise Model + Migration

- [x] 1.1 Create `backend/app/shared/models/exercise.py` with Exercise model
- [x] 1.2 Update `backend/app/shared/models/__init__.py` to re-export Exercise
- [x] 1.3 Create migration `backend/alembic/versions/004_exercises.py` with GIN index
- [x] 1.4 Update `backend/alembic/env.py` to import Exercise model

## 2. Schemas + Validation

- [x] 2.1 Create `backend/app/features/exercises/schemas.py` with TestCase, TestCaseSet, ExerciseCreateRequest, ExerciseResponse, ExerciseSummaryResponse

## 3. Repository

- [x] 3.1 Create `backend/app/features/exercises/repositories.py` with ExerciseRepository (filters by course, difficulty, topic_tags, student enrollment)

## 4. Service

- [x] 4.1 Create `backend/app/features/exercises/services.py` with ExerciseService (create with test_cases validation, reads_problem event for alumno)

## 5. Router + Registration

- [x] 5.1 Create `backend/app/features/exercises/router.py` with CRUD + student/exercises + RBAC
- [x] 5.2 Register exercises router in `backend/app/main.py`

## 6. Seed Data

- [x] 6.1 Create `infra/seed/03_exercises.py` with 3 exercises (easy/medium/hard)

## 7. Frontend — Store + Types

- [x] 7.1 Create `frontend/src/features/exercises/types.ts`
- [x] 7.2 Create `frontend/src/features/exercises/store.ts` with useExercisesStore (Zustand 5)

## 8. Frontend — Pages

- [x] 8.1 Create `frontend/src/features/exercises/ExercisesPage.tsx` — list with difficulty filter chips
- [x] 8.2 Create `frontend/src/features/exercises/ExerciseDetailPage.tsx` — detail with enunciado, test cases, starter code
- [x] 8.3 Create `frontend/src/features/exercises/ExerciseFormModal.tsx` — docente create form

## 9. App Integration

- [x] 9.1 Update `frontend/src/App.tsx` with exercise routes

## 10. Tests

- [x] 10.1 Create `backend/tests/integration/test_exercises.py`
