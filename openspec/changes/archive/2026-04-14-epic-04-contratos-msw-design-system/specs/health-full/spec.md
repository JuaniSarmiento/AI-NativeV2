## ADDED Requirements

### Requirement: Full health check endpoint
The system SHALL expose `GET /api/v1/health/full` returning the status of database and Redis connections.

#### Scenario: All services healthy
- **WHEN** DB and Redis are reachable
- **THEN** the response SHALL be 200 with `{ "status": "ok", "data": { "database": "ok", "redis": "ok" } }`

#### Scenario: Database unreachable
- **WHEN** the database connection fails
- **THEN** the response SHALL be 503 with `database: "error"` and the error message
