## ADDED Requirements

### Requirement: Exercise model in operational schema
The system SHALL have an `Exercise` model in the `operational` schema with fields: id (UUID PK), course_id (UUID FK courses.id, NOT NULL), title (VARCHAR 255, NOT NULL), description (TEXT, NOT NULL), test_cases (JSONB, NOT NULL), difficulty (ENUM: easy/medium/hard, NOT NULL), topic_tags (TEXT[], NOT NULL, DEFAULT '{}'), language (VARCHAR 50, default 'python'), starter_code (TEXT, default ''), max_attempts (SMALLINT, default 10), time_limit_minutes (SMALLINT, default 60), order_index (SMALLINT, default 0), is_active (BOOLEAN, default true), created_at, updated_at.

#### Scenario: Exercise belongs to a course
- **WHEN** an Exercise is created with a valid course_id
- **THEN** it SHALL have a `course` relationship pointing to the parent Course

#### Scenario: topic_tags supports array containment queries
- **WHEN** a query filters exercises where topic_tags contains 'recursion'
- **THEN** the database SHALL use the GIN index for efficient lookup

### Requirement: Alembic migration 004 for exercises
The system SHALL have a migration creating the `exercises` table with difficulty ENUM, GIN index on topic_tags, and indexes on course_id.

#### Scenario: Migration creates GIN index
- **WHEN** migration 004 is applied
- **THEN** an index `ix_exercises_topic_tags_gin` of type GIN SHALL exist on the topic_tags column

### Requirement: Test cases JSONB schema validation
The system SHALL validate test_cases JSONB structure via Pydantic before persisting. The expected structure: `{ language: str, timeout_ms: int, memory_limit_mb: int, cases: [{ id: str, description: str, input: str, expected_output: str, is_hidden: bool, weight: float }] }`.

#### Scenario: Invalid test_cases rejected
- **WHEN** an exercise is created with test_cases missing required fields
- **THEN** the service SHALL raise a ValidationError before reaching the database
