## ADDED Requirements

### Requirement: Production Docker Compose
The system SHALL provide a docker-compose.prod.yml with production-optimized settings.

#### Scenario: Production deploy
- **WHEN** `docker compose -f devOps/docker-compose.prod.yml up -d` is executed
- **THEN** all services SHALL start with healthchecks, restart policies, and persistent volumes

### Requirement: Database backup script
The system SHALL provide a backup script that dumps the database daily with 7-day rotation.

#### Scenario: Backup runs
- **WHEN** the backup script executes
- **THEN** a timestamped pg_dump file SHALL be created and files older than 7 days SHALL be removed

### Requirement: Deploy documentation
The system SHALL provide deploy and rollback documentation.

#### Scenario: New developer deploys
- **WHEN** a developer reads the deploy guide
- **THEN** they SHALL be able to deploy the system from scratch
