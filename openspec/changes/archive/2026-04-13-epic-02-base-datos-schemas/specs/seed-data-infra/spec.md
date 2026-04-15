## ADDED Requirements

### Requirement: Seed data infrastructure
The system SHALL provide a seed data mechanism at `infra/seed/` with a runner script that executes seed files in order. Each seed file SHALL export an async `seed(session)` function.

#### Scenario: Running seeds creates base data
- **WHEN** `make seed` is executed against an empty database (with schemas and tables created)
- **THEN** it SHALL create: 1 admin user, 1 docente user, 1 alumno user, 1 course with topic_taxonomy, 1 commission linked to the course and docente

#### Scenario: Seeds are idempotent
- **WHEN** `make seed` is executed twice
- **THEN** it SHALL not create duplicate records (check by email for users, by name for courses)

#### Scenario: Seed runner uses UoW for transactions
- **WHEN** seeds are executed
- **THEN** each seed file SHALL run within an AsyncUnitOfWork context so failures roll back cleanly

### Requirement: Extensible seed structure
Each future EPIC SHALL be able to add its own seed file (e.g., `infra/seed/03_exercises.py`) that the runner picks up automatically by filename order.

#### Scenario: New seed file is picked up
- **WHEN** a new file `infra/seed/03_exercises.py` is added with a `seed(session)` function
- **THEN** the runner SHALL execute it after `02_base_data.py` based on filename sort order
