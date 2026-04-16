## ADDED Requirements

### Requirement: Admin endpoint to list governance events
The system SHALL expose GET /api/v1/governance/events for admin users with pagination and filtering.

#### Scenario: Admin retrieves all events paginated
- **WHEN** an admin sends GET /api/v1/governance/events?page=1&per_page=20
- **THEN** the system SHALL return events ordered by created_at DESC with pagination meta

#### Scenario: Admin filters by event_type
- **WHEN** an admin sends GET /api/v1/governance/events?event_type=guardrail.triggered
- **THEN** the system SHALL return only matching events

#### Scenario: Non-admin access denied
- **WHEN** a non-admin user sends GET /api/v1/governance/events
- **THEN** the system SHALL return 403 Forbidden

#### Scenario: No events exist
- **WHEN** an admin queries and no events exist
- **THEN** the system SHALL return empty list with 200 status
