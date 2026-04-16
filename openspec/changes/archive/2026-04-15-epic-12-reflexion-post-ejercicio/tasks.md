## 1. Reflection Model + Migration

- [x] 1.1 Create Reflection SQLAlchemy model in `app/features/submissions/models.py`
- [x] 1.2 Generate Alembic migration for operational.reflections table

## 2. Reflection Service + Schemas

- [x] 2.1 Add Pydantic schemas: CreateReflectionRequest, ReflectionResponse
- [x] 2.2 Create ReflectionService with create_reflection() and get_reflection()
- [x] 2.3 Validate: submission must exist and belong to student, only one reflection per activity_submission
- [x] 2.4 Emit reflection.submitted EventOutbox on create

## 3. Reflection API Endpoints

- [x] 3.1 POST /api/v1/submissions/{activity_submission_id}/reflection
- [x] 3.2 GET /api/v1/submissions/{activity_submission_id}/reflection
- [x] 3.3 Add RBAC: alumno can only see own, docente can see from their commission

## 4. Frontend — Reflection Form

- [x] 4.1 Create ReflectionForm component with 5 guided fields
- [x] 4.2 Integrate in StudentActivityViewPage: after submit, show ReflectionForm
- [x] 4.3 Add "Saltar reflexion" link for optional skip
- [x] 4.4 Client-side validation: all fields required, text fields min 10 chars

## 5. Frontend — Read-only View

- [x] 5.1 Create ReflectionView component showing submitted reflection read-only
- [x] 5.2 Show ReflectionView when reflection already exists for the submission
- [ ] 5.3 Docente: show reflection in submission detail view

## 6. Outbox Routing

- [x] 6.1 Add "reflection" prefix routing in outbox_worker.py → events:submissions stream

## 7. Tests

- [x] 7.1 Unit tests for ReflectionService: create, duplicate prevention, RBAC validation
- [x] 7.2 Integration tests for reflection endpoints: create, read, permissions
- [x] 7.3 Test reflection.submitted event emission
