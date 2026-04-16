## ADDED Requirements

### Requirement: Governance reports page
The system SHALL provide a page at route `/admin/governance` displaying governance events and prompt history. Requires role admin.

#### Scenario: Navigation to governance
- **WHEN** an admin navigates to `/admin/governance`
- **THEN** the page SHALL display tabs for "Eventos" and "Prompts"

### Requirement: Governance events table
The system SHALL display a paginated table of governance events from `GET /api/v1/governance/events`. Columns: event_type, actor_id, target_type, details summary, created_at. Supports filtering by event_type.

#### Scenario: Filter by guardrail violations
- **WHEN** an admin selects event_type "guardrail.triggered"
- **THEN** only guardrail violation events SHALL be shown

#### Scenario: Pagination
- **WHEN** more than 20 events exist
- **THEN** pagination controls SHALL allow navigating between pages

### Requirement: Prompt history table
The system SHALL display a table of system prompts from `GET /api/v1/governance/prompts`. Columns: name, version, sha256_hash (truncated), is_active (badge), created_at. The active prompt SHALL be highlighted.

#### Scenario: Active prompt highlight
- **WHEN** a prompt has is_active=true
- **THEN** the row SHALL display a green "Activo" badge

### Requirement: Integrity alerts
The system SHALL display a section showing any cognitive sessions with compromised hash chains. This section fetches sessions from the commission and verifies each via the existing verify endpoint.

#### Scenario: No compromised sessions
- **WHEN** all sessions pass verification
- **THEN** the section SHALL show "Sin alertas de integridad"

#### Scenario: Compromised session found
- **WHEN** a session fails verification
- **THEN** the section SHALL show the session ID and the sequence number where tampering was detected
