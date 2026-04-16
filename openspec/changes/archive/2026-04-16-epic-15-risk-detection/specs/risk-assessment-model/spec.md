## ADDED Requirements

### Requirement: RiskAssessment model in analytics schema
The system SHALL provide a `RiskAssessment` SQLAlchemy model in the `analytics` schema. Fields: `id` (UUID PK, server_default gen_random_uuid()), `student_id` (UUID NOT NULL, no FK — cross-schema), `commission_id` (UUID NOT NULL, no FK — cross-schema), `risk_level` (String(20) NOT NULL — low/medium/high/critical), `risk_factors` (JSONB NOT NULL), `recommendation` (TEXT NULLABLE), `triggered_by` (String(20) NOT NULL — automatic/manual/threshold), `assessed_at` (TIMESTAMPTZ NOT NULL, server_default now()), `acknowledged_by` (UUID NULLABLE), `acknowledged_at` (TIMESTAMPTZ NULLABLE). The model SHALL use String types (not PostgreSQL ENUM) to avoid DuplicateObjectError on repeated schema creation.

#### Scenario: Model table creation
- **WHEN** Alembic migration runs
- **THEN** table `analytics.risk_assessments` is created with all specified columns, indexes on `student_id`, `commission_id`, and `risk_level`

#### Scenario: risk_factors JSONB structure
- **WHEN** a RiskAssessment is created
- **THEN** `risk_factors` SHALL contain a dict with factor names as keys (e.g. "dependency", "disengagement", "stagnation") and each value SHALL be a dict with at least a `score` field (float 0-1)

#### Scenario: Acknowledge fields default to null
- **WHEN** a RiskAssessment is created without acknowledge data
- **THEN** `acknowledged_by` and `acknowledged_at` SHALL be NULL

### Requirement: Unique constraint for idempotency
The system SHALL enforce a unique constraint on `(student_id, commission_id, assessed_at::date)` to prevent duplicate assessments for the same student, commission, and day.

#### Scenario: Duplicate assessment prevention
- **WHEN** the RiskWorker runs twice on the same day for the same student/commission
- **THEN** the second run SHALL update the existing row instead of creating a new one

### Requirement: Alembic migration for risk_assessments
The system SHALL provide an Alembic migration that creates `analytics.risk_assessments` with proper indexes and the unique constraint.

#### Scenario: Migration up
- **WHEN** `alembic upgrade head` runs
- **THEN** the `analytics.risk_assessments` table is created with all indexes and constraints

#### Scenario: Migration down
- **WHEN** `alembic downgrade` runs
- **THEN** the `analytics.risk_assessments` table is dropped cleanly

### Requirement: RiskAssessmentRepository
The system SHALL provide a `RiskAssessmentRepository` extending `BaseRepository[RiskAssessment]` with methods: `get_by_commission(commission_id, page, per_page)` returning paginated list filtered by commission, `get_by_student(student_id, page, per_page)` returning paginated history for a student, `get_active_by_student_commission(student_id, commission_id)` returning the most recent unacknowledged assessment, and `upsert_daily(assessment_data)` performing insert-or-update by (student_id, commission_id, today).

#### Scenario: Paginated commission query
- **WHEN** `get_by_commission` is called with a commission_id
- **THEN** it SHALL return risk assessments ordered by `assessed_at DESC` with pagination metadata

#### Scenario: Upsert daily idempotency
- **WHEN** `upsert_daily` is called twice on the same day for the same student/commission
- **THEN** only one row SHALL exist, updated with the latest data
