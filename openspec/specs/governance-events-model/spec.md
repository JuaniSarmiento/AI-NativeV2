## Purpose
GovernanceEvent SQLAlchemy model in governance schema for audit trail of policy events.

## Requirements

### Requirement: GovernanceEvent model
Model with: id UUID PK, event_type VARCHAR(100) NOT NULL, actor_id UUID NOT NULL, target_type/target_id nullable, details JSONB NOT NULL, created_at TIMESTAMPTZ.

#### Scenario: Correct columns
- **WHEN** the model is defined
- **THEN** it SHALL have all specified columns in schema governance

#### Scenario: VARCHAR event_type not DB enum
- **WHEN** events are created
- **THEN** event_type SHALL be VARCHAR(100), not PostgreSQL enum

### Requirement: Alembic migration
Migration creates governance.governance_events with indices on event_type and actor_id.

#### Scenario: Migration runs
- **WHEN** alembic upgrade head
- **THEN** table created with indices

#### Scenario: Reversible
- **WHEN** alembic downgrade
- **THEN** table dropped
