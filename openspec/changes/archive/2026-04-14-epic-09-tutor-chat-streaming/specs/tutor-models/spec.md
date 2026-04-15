## ADDED Requirements

### Requirement: tutor_interactions model in operational schema
The system SHALL provide a `tutor_interactions` table in the `operational` schema that records every chat turn.

#### Scenario: Interaction record is persisted after LLM response
- **WHEN** the tutor completes a response to an alumno message
- **THEN** a `tutor_interactions` record SHALL be created with: `id` (UUID PK), `session_id` (UUID NOT NULL — correlación lógica con cognitive_sessions, sin FK cross-schema), `student_id` (UUID FK → users), `exercise_id` (UUID FK → exercises), `role` (ENUM: user/assistant), `content` (TEXT NOT NULL), `n4_level` (SMALLINT NULLABLE, CHECK 1-4), `tokens_used` (INTEGER NULLABLE), `model_version` (VARCHAR 100 NULLABLE), `prompt_hash` (VARCHAR 64 NOT NULL), `created_at` (TIMESTAMPTZ)

#### Scenario: Both user and assistant turns are recorded
- **WHEN** an alumno sends a message and receives a response
- **THEN** TWO `tutor_interactions` records SHALL be created: one with `role=user` (the alumno's message) and one with `role=assistant` (the tutor's response)

#### Scenario: prompt_hash is SHA-256 of active system prompt
- **WHEN** a tutor_interaction is created
- **THEN** `prompt_hash` SHALL be the SHA-256 hash of the system prompt that was active at the time of the interaction

### Requirement: tutor_system_prompts model in governance schema
The system SHALL provide a `tutor_system_prompts` table in the `governance` schema for versioned system prompts.

#### Scenario: System prompt is created with SHA-256
- **WHEN** a new system prompt version is created
- **THEN** it SHALL have: `id` (UUID PK), `name` (VARCHAR), `content` (TEXT), `sha256_hash` (VARCHAR 64 — computed from content), `version` (VARCHAR 50 NOT NULL), `is_active` (BOOL DEFAULT FALSE), `guardrails_config` (JSONB NULLABLE), `created_by` (UUID NOT NULL), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ NOT NULL)

#### Scenario: Only one prompt is active at a time
- **WHEN** a prompt is set as `is_active = TRUE`
- **THEN** all other prompts SHALL be set to `is_active = FALSE`

### Requirement: Alembic migrations
The system SHALL include Alembic migrations for both tables.

#### Scenario: Migration creates tutor_interactions in operational schema
- **WHEN** the migration runs
- **THEN** `operational.tutor_interactions` SHALL exist with all columns, indexes on `student_id`, `exercise_id`, and `session_id`

#### Scenario: Migration creates tutor_system_prompts in governance schema
- **WHEN** the migration runs
- **THEN** `governance.tutor_system_prompts` SHALL exist with all columns and a unique index on `sha256_hash`

#### Scenario: Seed data includes basic system prompt
- **WHEN** the migration or seed script runs
- **THEN** a default system prompt version SHALL exist with `is_active=TRUE`, containing the basic socratic tutor instructions
