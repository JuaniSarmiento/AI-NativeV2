## 1. Domain Models

- [x] 1.1 Create `backend/app/shared/models/user.py` with User model (UUID PK, email unique, password_hash, full_name, role ENUM, is_active, timestamps) in schema operational
- [x] 1.2 Create `backend/app/shared/models/course.py` with Course model (UUID PK, name, description, topic_taxonomy JSONB nullable, is_active, timestamps) in schema operational, with `commissions` relationship
- [x] 1.3 Create `backend/app/shared/models/commission.py` with Commission model (UUID PK, course_id FK, teacher_id FK, name, year, semester, is_active, timestamps) in schema operational, with `course` and `teacher` relationships
- [x] 1.4 Update `backend/app/shared/models/__init__.py` to re-export User, Course, Commission, EventOutbox

## 2. Alembic Migration

- [x] 2.1 Create migration `backend/alembic/versions/002_base_domain_models.py` with tables users, courses, commissions in operational schema, including user_role ENUM type, all indexes and constraints
- [x] 2.2 Update `backend/alembic/env.py` to import User, Course, Commission models

## 3. Base Repository

- [x] 3.1 Create `backend/app/shared/repositories/base.py` with `BaseRepository[ModelType]` generic class: get_by_id, list (paginated), create, update, soft_delete, configurable load_options
- [x] 3.2 Update `backend/app/shared/repositories/__init__.py` to re-export BaseRepository

## 4. Seed Data Infrastructure

- [x] 4.1 Create `infra/seed/__init__.py` and `infra/seed/runner.py` with async seed runner that discovers and executes seed files in filename order using UoW
- [x] 4.2 Create `infra/seed/01_base_data.py` with idempotent seed: 1 admin, 1 docente, 1 alumno, 1 course with topic_taxonomy, 1 commission
- [x] 4.3 Update `Makefile` target `seed` to run the seed runner

## 5. Testing

- [x] 5.1 Update `backend/tests/conftest.py` to import and register all new models
- [x] 5.2 Create `backend/tests/unit/test_base_repository.py` with tests for get_by_id, list, create, update, soft_delete, and load_options
