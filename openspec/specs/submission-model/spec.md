## ADDED Requirements

### Requirement: Submission model
The system SHALL have a `Submission` model in operational schema with: id (UUID PK), student_id (FK users), exercise_id (FK exercises), activity_submission_id (FK activity_submissions, nullable), code (TEXT NOT NULL), status (ENUM: pending/evaluated, default pending), score (NUMERIC 5,2 nullable — set by AI evaluator later), feedback (TEXT nullable), attempt_number (SMALLINT default 1), submitted_at (TIMESTAMPTZ), evaluated_at (TIMESTAMPTZ nullable).

#### Scenario: Submission created on activity submit
- **WHEN** a student submits an activity
- **THEN** one Submission per exercise SHALL be created with the student's code and status "pending"

### Requirement: CodeSnapshot model (immutable)
The system SHALL have a `CodeSnapshot` model with: id (UUID PK), student_id (UUID), exercise_id (UUID), code (TEXT), snapshot_at (TIMESTAMPTZ). There SHALL be NO update or delete endpoints.

#### Scenario: Snapshot is immutable
- **WHEN** a snapshot is saved
- **THEN** it SHALL never be modified or deleted

### Requirement: ActivitySubmission model
The system SHALL have an `ActivitySubmission` model with: id (UUID PK), activity_id (FK activities), student_id (FK users), attempt_number (SMALLINT), status (ENUM: pending/evaluated), submitted_at (TIMESTAMPTZ), total_score (NUMERIC 5,2 nullable).

#### Scenario: Activity submission groups exercise submissions
- **WHEN** a student submits an activity
- **THEN** an ActivitySubmission SHALL be created linking to N Submissions (one per exercise)

### Requirement: Migration 008
The system SHALL have a migration creating submissions, code_snapshots, and activity_submissions tables.

#### Scenario: Migration runs successfully
- **WHEN** migration 008 is applied
- **THEN** all three tables SHALL exist with correct constraints
