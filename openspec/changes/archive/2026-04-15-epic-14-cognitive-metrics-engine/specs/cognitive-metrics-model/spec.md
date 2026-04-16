## ADDED Requirements

### Requirement: CognitiveMetrics model in cognitive schema
The system SHALL provide a `CognitiveMetrics` SQLAlchemy model in the `cognitive` schema with a one-to-one relationship to `CognitiveSession`. All score fields SHALL use `NUMERIC` types (not FLOAT). The model SHALL include: `n1_comprehension_score` (NUMERIC(5,2)), `n2_strategy_score` (NUMERIC(5,2)), `n3_validation_score` (NUMERIC(5,2)), `n4_ai_interaction_score` (NUMERIC(5,2)), `total_interactions` (INTEGER NOT NULL DEFAULT 0), `help_seeking_ratio` (NUMERIC(4,3)), `autonomy_index` (NUMERIC(4,3)), `qe_score` (NUMERIC(5,2)), `qe_quality_prompt` (NUMERIC(5,2)), `qe_critical_evaluation` (NUMERIC(5,2)), `qe_integration` (NUMERIC(5,2)), `qe_verification` (NUMERIC(5,2)), `dependency_score` (NUMERIC(4,3)), `reflection_score` (NUMERIC(5,2)), `success_efficiency` (NUMERIC(5,2)), `risk_level` (VARCHAR — low/medium/high/critical), `computed_at` (TIMESTAMPTZ).

#### Scenario: Model table creation
- **WHEN** Alembic migration runs
- **THEN** table `cognitive.cognitive_metrics` is created with all specified columns and a UNIQUE constraint on `session_id`

#### Scenario: Unique session constraint
- **WHEN** a second `CognitiveMetrics` row is inserted for the same `session_id`
- **THEN** the database SHALL raise an IntegrityError

### Requirement: ReasoningRecord model in cognitive schema
The system SHALL provide a `ReasoningRecord` SQLAlchemy model in the `cognitive` schema. Records are IMMUTABLE — no UPDATE or DELETE operations. Fields: `id` (UUID PK), `session_id` (UUID FK → cognitive_sessions.id NOT NULL), `record_type` (VARCHAR — hypothesis/strategy/validation/reflection NOT NULL), `details` (JSONB NOT NULL), `previous_hash` (VARCHAR(64) NOT NULL), `event_hash` (VARCHAR(64) NOT NULL), `created_at` (TIMESTAMPTZ NOT NULL). The model SHALL have an index on `session_id`.

#### Scenario: ReasoningRecord creation with hash chain
- **WHEN** a ReasoningRecord is created
- **THEN** `event_hash` SHALL equal `SHA256(previous_hash + ':' + record_type + ':' + sorted_json(details) + ':' + created_at_iso)`

#### Scenario: Immutability enforcement
- **WHEN** code attempts to UPDATE or DELETE a ReasoningRecord
- **THEN** the operation SHALL be rejected (enforced at application layer — service never exposes update/delete)

### Requirement: Alembic migration for both tables
The system SHALL provide a single Alembic migration that creates both `cognitive.cognitive_metrics` and `cognitive.reasoning_records` tables with proper indexes.

#### Scenario: Migration up
- **WHEN** `alembic upgrade head` runs
- **THEN** both tables are created in the `cognitive` schema with all indexes and constraints

#### Scenario: Migration down
- **WHEN** `alembic downgrade` runs
- **THEN** both tables are dropped cleanly
