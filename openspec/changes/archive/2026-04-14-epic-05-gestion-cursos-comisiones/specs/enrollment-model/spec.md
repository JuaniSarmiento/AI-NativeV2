## ADDED Requirements

### Requirement: Enrollment model in operational schema
The system SHALL have an `Enrollment` model in the `operational` schema with fields: id (UUID PK), student_id (UUID FK users.id, NOT NULL), commission_id (UUID FK commissions.id, NOT NULL), enrolled_at (TIMESTAMPTZ, server default now), is_active (BOOLEAN default true). UNIQUE constraint on (student_id, commission_id).

#### Scenario: Enrollment links student to commission
- **WHEN** an Enrollment is created with a valid student_id and commission_id
- **THEN** it SHALL persist and be retrievable with its relationships

#### Scenario: Duplicate enrollment rejected at DB level
- **WHEN** an Enrollment with the same student_id and commission_id already exists
- **THEN** the database SHALL raise an IntegrityError

### Requirement: Alembic migration 003 for enrollments
The system SHALL have a migration creating the `enrollments` table in `operational` schema with unique constraint and indexes on student_id and commission_id.

#### Scenario: Migration runs after 002
- **WHEN** migration 003 is applied
- **THEN** the enrollments table SHALL exist with all constraints
