## ADDED Requirements

### Requirement: User model in operational schema
The system SHALL have a `User` model in the `operational` schema with fields: id (UUID PK, server-generated), email (VARCHAR, UNIQUE, NOT NULL), password_hash (VARCHAR 128, NOT NULL), full_name (VARCHAR 255, NOT NULL), role (PostgreSQL ENUM: alumno/docente/admin, NOT NULL), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ, server default now), updated_at (TIMESTAMPTZ, server default now, auto-update on modification).

#### Scenario: User model maps to operational schema
- **WHEN** the User model is defined
- **THEN** it SHALL use `__tablename__ = "users"` and `__table_args__ = {"schema": "operational"}`

#### Scenario: Email uniqueness enforced at DB level
- **WHEN** a User with an existing email is inserted
- **THEN** the database SHALL raise an IntegrityError due to the unique constraint

#### Scenario: Role validation at DB level
- **WHEN** a User is created with a role not in (alumno, docente, admin)
- **THEN** the database SHALL reject the insert

### Requirement: Course model in operational schema
The system SHALL have a `Course` model in the `operational` schema with fields: id (UUID PK, server-generated), name (VARCHAR 255, NOT NULL), description (TEXT, NULLABLE), topic_taxonomy (JSONB, NULLABLE — hierarchical topic tree), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ, server default now), updated_at (TIMESTAMPTZ, server default now, auto-update).

#### Scenario: Course has relationship to commissions
- **WHEN** a Course is loaded with its commissions
- **THEN** the Course SHALL have a `commissions` relationship that returns all associated Commission objects

#### Scenario: topic_taxonomy accepts nested JSON
- **WHEN** a Course is created with a nested JSON object in topic_taxonomy
- **THEN** the field SHALL store and retrieve the full JSON structure

### Requirement: Commission model in operational schema
The system SHALL have a `Commission` model in the `operational` schema with fields: id (UUID PK, server-generated), course_id (UUID FK → courses.id, NOT NULL), teacher_id (UUID FK → users.id, NOT NULL), name (VARCHAR 255, NOT NULL), year (SMALLINT, NOT NULL), semester (SMALLINT, NOT NULL), is_active (BOOLEAN default true), created_at (TIMESTAMPTZ, server default now), updated_at (TIMESTAMPTZ, server default now, auto-update).

#### Scenario: Commission belongs to a course
- **WHEN** a Commission is loaded
- **THEN** it SHALL have a `course` relationship pointing to the parent Course

#### Scenario: Commission has a teacher reference
- **WHEN** a Commission is loaded
- **THEN** it SHALL have a `teacher` relationship pointing to the User who is the teacher

#### Scenario: Cascade delete protection
- **WHEN** a Course with associated Commissions is deleted
- **THEN** the database SHALL prevent the deletion (restrict) or the application SHALL use soft delete

### Requirement: Alembic migration 002 for base models
The system SHALL have a migration `002_base_domain_models` that creates tables `users`, `courses`, and `commissions` in the `operational` schema with all columns, constraints, indexes, and the `user_role` ENUM type.

#### Scenario: Migration runs successfully after 001
- **WHEN** migration 002 is applied after 001
- **THEN** tables users, courses, commissions SHALL exist in the operational schema with all defined columns and constraints

#### Scenario: Migration downgrades cleanly
- **WHEN** migration 002 is downgraded
- **THEN** tables users, courses, commissions and the user_role ENUM type SHALL be dropped

### Requirement: Models registered in alembic env.py
All new models SHALL be imported in `backend/alembic/env.py` so Alembic autogenerate can detect future schema drifts.

#### Scenario: Alembic sees all models
- **WHEN** `alembic check` is run after migration 002
- **THEN** it SHALL report no pending changes for the users, courses, and commissions tables
