## ADDED Requirements

### Requirement: Prompt history endpoint
The system SHALL provide `GET /api/v1/governance/prompts` returning a paginated list of TutorSystemPrompt records with fields: id, name, version, sha256_hash, is_active, created_at. Supports `page` and `per_page` query params. Requires role admin.

#### Scenario: List all prompts
- **WHEN** an admin calls GET `/api/v1/governance/prompts`
- **THEN** the system SHALL return all system prompts ordered by created_at DESC

#### Scenario: Active prompt highlighted
- **WHEN** the list includes both active and inactive prompts
- **THEN** the `is_active` field SHALL correctly reflect the current state of each prompt

#### Scenario: Non-admin denied
- **WHEN** a docente calls this endpoint
- **THEN** the system SHALL return 403 Forbidden
