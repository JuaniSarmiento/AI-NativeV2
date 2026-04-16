## ADDED Requirements

### Requirement: CognitiveSession model in cognitive schema
The system SHALL have a CognitiveSession model tracking student work sessions per exercise.

#### Scenario: Model has all specified columns
- **WHEN** the CognitiveSession model is defined
- **THEN** it SHALL have: id UUID PK, student_id UUID NOT NULL, exercise_id UUID NOT NULL, commission_id UUID NOT NULL, started_at TIMESTAMPTZ, closed_at TIMESTAMPTZ nullable, genesis_hash VARCHAR(64) nullable, session_hash VARCHAR(64) nullable, n4_final_score JSONB nullable, status ENUM(open/closed/invalidated)

### Requirement: CognitiveEvent model in cognitive schema
The system SHALL have an immutable CognitiveEvent model for hash-chained CTR entries.

#### Scenario: Model has all specified columns
- **WHEN** the CognitiveEvent model is defined
- **THEN** it SHALL have: id UUID PK, session_id UUID FK, event_type VARCHAR(100), sequence_number INTEGER, payload JSONB, previous_hash VARCHAR(64), event_hash VARCHAR(64), created_at TIMESTAMPTZ

#### Scenario: Unique constraint on session + sequence
- **WHEN** two events have the same session_id and sequence_number
- **THEN** the database SHALL reject the duplicate via UNIQUE constraint

### Requirement: Alembic migration for cognitive schema tables
Migration SHALL create both tables with proper indices and constraints.

#### Scenario: Migration creates both tables
- **WHEN** alembic upgrade head runs
- **THEN** cognitive.cognitive_sessions and cognitive.cognitive_events SHALL be created
