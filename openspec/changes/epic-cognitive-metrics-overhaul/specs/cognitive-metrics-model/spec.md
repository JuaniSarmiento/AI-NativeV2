## MODIFIED Requirements

### Requirement: CognitiveEvent model fields
The CognitiveEvent model SHALL include a `n4_level` column as Integer nullable, representing the N1-N4 observation level (1-4) or None for lifecycle events. A B-tree index SHALL exist on this column.

#### Scenario: Event with n4_level populated
- **WHEN** consumer persists a classified event with n4_level=2
- **THEN** the `n4_level` column stores integer 2 directly (not only in payload JSONB)

#### Scenario: Lifecycle event without level
- **WHEN** consumer persists a session.started event
- **THEN** the `n4_level` column is NULL

#### Scenario: Query events by level
- **WHEN** system queries `SELECT * FROM cognitive_events WHERE n4_level = 1`
- **THEN** query uses the B-tree index and returns only N1-classified events

## ADDED Requirements

### Requirement: CognitiveMetrics includes score_breakdown
The CognitiveMetrics model SHALL include a `score_breakdown` JSONB column storing the detailed reasoning for each N-score computation.

#### Scenario: Score breakdown persisted
- **WHEN** MetricsEngine computes metrics for a session
- **THEN** `score_breakdown` contains structured data: `{n1: [{condition, met, points}...], n2: [...], n3: [...], n4: [...]}`

### Requirement: CognitiveMetrics includes engine_version
The CognitiveMetrics model SHALL include an `engine_version` String(10) column storing the version of MetricsEngine that produced the scores (e.g., "2.0").

#### Scenario: New computation
- **WHEN** MetricsEngine v2 computes scores
- **THEN** `engine_version` = "2.0"

### Requirement: Alembic migration for schema changes
An Alembic migration SHALL add `n4_level` column, its index, `score_breakdown` column, and `engine_version` column.

#### Scenario: Migration applied on clean database
- **WHEN** `alembic upgrade head` runs
- **THEN** all new columns and indices exist on the target tables
