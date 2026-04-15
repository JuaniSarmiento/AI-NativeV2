## ADDED Requirements

### Requirement: Activity model in operational schema
The system SHALL have an `Activity` model with fields: id (UUID PK), course_id (FK courses), created_by (FK users), title (VARCHAR 255), description (TEXT), prompt_used (TEXT — the docente's original instruction), status (ENUM: draft/published), is_active (BOOLEAN), created_at, updated_at. Each Activity has a one-to-many relationship with Exercises.

#### Scenario: Activity groups exercises
- **WHEN** an Activity is created with 3 exercises
- **THEN** the activity SHALL have an `exercises` relationship returning those 3 exercises

#### Scenario: Draft activity has inactive exercises
- **WHEN** an Activity is in draft status
- **THEN** its exercises SHALL have is_active=False until the activity is published

### Requirement: Activity exercises link
The Exercise model SHALL have a nullable `activity_id` (FK activities.id) field so exercises can optionally belong to an activity. Exercises without activity_id are standalone.

#### Scenario: Exercise belongs to activity
- **WHEN** an exercise has an activity_id
- **THEN** it SHALL be retrievable via the activity's exercises relationship

### Requirement: Alembic migration for activities
The system SHALL have a migration creating the `activities` table and adding `activity_id` column to `exercises`.

#### Scenario: Migration runs successfully
- **WHEN** the migration is applied
- **THEN** tables activities SHALL exist and exercises.activity_id SHALL be nullable FK
