## Purpose
Admin-only REST endpoint for querying governance events with pagination and filtering.

## Requirements

### Requirement: Admin endpoint to list governance events
GET /api/v1/governance/events — admin only, paginated, filterable by event_type.

#### Scenario: Admin retrieves paginated
- **WHEN** admin sends GET with page/per_page
- **THEN** returns events ordered by created_at DESC with pagination meta

#### Scenario: Filter by event_type
- **WHEN** admin sends ?event_type=guardrail.triggered
- **THEN** returns only matching events

#### Scenario: Non-admin denied
- **WHEN** non-admin user sends request
- **THEN** 403 Forbidden

#### Scenario: Empty list
- **WHEN** no events exist
- **THEN** returns empty data with 200 status
