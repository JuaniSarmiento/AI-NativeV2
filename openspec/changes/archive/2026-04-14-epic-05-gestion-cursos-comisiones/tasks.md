## 1. Enrollment Model + Migration

- [x] 1.1 Create `backend/app/shared/models/enrollment.py` with Enrollment model (UUID PK, student_id FK, commission_id FK, enrolled_at, is_active, UNIQUE constraint)
- [x] 1.2 Update `backend/app/shared/models/__init__.py` to re-export Enrollment
- [x] 1.3 Create migration `backend/alembic/versions/003_enrollments.py` with enrollments table + indexes + unique constraint
- [x] 1.4 Update `backend/alembic/env.py` to import Enrollment model

## 2. Repositories

- [x] 2.1 Create `backend/app/features/courses/repositories.py` with CourseRepository, CommissionRepository, EnrollmentRepository extending BaseRepository

## 3. Schemas

- [x] 3.1 Create `backend/app/features/courses/schemas.py` with Pydantic v2 request/response models for courses, commissions, enrollments

## 4. Domain Services

- [x] 4.1 Create `backend/app/features/courses/services.py` with CourseService (create, update, delete, list), CommissionService (create, update, delete, list), EnrollmentService (enroll with outbox event, list student courses)

## 5. Router + Registration

- [x] 5.1 Create `backend/app/features/courses/router.py` with all endpoints (CRUD courses, CRUD commissions, enroll, student/courses) with RBAC
- [x] 5.2 Register courses router in `backend/app/main.py`

## 6. Seed Data

- [x] 6.1 Create `infra/seed/02_courses_enrollments.py` with 2 courses, 3 commissions, 2 enrollments

## 7. Frontend — Stores + Types

- [x] 7.1 Create `frontend/src/features/courses/types.ts` with Course, Commission, Enrollment types
- [x] 7.2 Create `frontend/src/features/courses/store.ts` with useCoursesStore (Zustand 5)

## 8. Frontend — Docente Pages

- [x] 8.1 Create `frontend/src/features/courses/CoursesPage.tsx` — list courses, create/edit modal, delete
- [x] 8.2 Create `frontend/src/features/courses/CourseDetailPage.tsx` — course detail with commissions list, create/edit commission

## 9. Frontend — Alumno Pages

- [x] 9.1 Create `frontend/src/features/courses/StudentCoursesPage.tsx` — enrolled courses + enroll action

## 10. App Integration

- [x] 10.1 Update `frontend/src/App.tsx` with course routes (docente: /courses, /courses/:id; alumno: /courses)
- [x] 10.2 Create `frontend/src/mocks/handlers/courses.ts` with MSW handlers for all endpoints
- [x] 10.3 Update `frontend/src/mocks/handlers/index.ts` to include courses handlers

## 11. Tests

- [x] 11.1 Create `backend/tests/integration/test_courses.py` with tests for CRUD + RBAC + pagination + enrollment
