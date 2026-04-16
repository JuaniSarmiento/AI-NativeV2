## ADDED Requirements

### Requirement: GovernanceEvent SQLAlchemy model in governance schema
The system SHALL have a GovernanceEvent model with event_type VARCHAR(100), actor_id UUID NOT NULL, target_type/target_id nullable, details JSONB NOT NULL.

#### Scenario: Model has correct columns
- **WHEN** the GovernanceEvent model is defined
- **THEN** it SHALL have: id, event_type, actor_id, target_type, target_id, details, created_at

#### Scenario: event_type is not a DB enum
- **WHEN** governance events are created
- **THEN** event_type SHALL be VARCHAR(100) with application-level conventions

### Requirement: Alembic migration creates governance_events table
An Alembic migration SHALL create the governance.governance_events table.

#### Scenario: Migration runs successfully
- **WHEN** alembic upgrade head is run
- **THEN** the table SHALL be created with indices on event_type and actor_id

#### Scenario: Migration is reversible
- **WHEN** alembic downgrade is run
- **THEN** the table SHALL be dropped
