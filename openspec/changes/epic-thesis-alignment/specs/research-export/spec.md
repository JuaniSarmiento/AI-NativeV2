## ADDED Requirements

### Requirement: Export cognitive data for research
The system SHALL provide an endpoint `GET /api/v1/admin/export/cognitive-data` that returns structured cognitive session data for statistical analysis.

#### Scenario: Admin exports all data as JSON
- **WHEN** an admin user requests `/api/v1/admin/export/cognitive-data?format=json`
- **THEN** the system SHALL return all cognitive sessions with their metrics (N1-N4, Qe, coherences), events per session, and metadata
- **THEN** the response format SHALL be JSON

#### Scenario: Admin exports filtered data as CSV
- **WHEN** an admin requests with `?format=csv&commission_id=X&date_from=2026-01-01&date_to=2026-06-30`
- **THEN** the system SHALL return only sessions matching the filters
- **THEN** the response SHALL be a downloadable CSV file with one row per session

#### Scenario: Non-admin user attempts export
- **WHEN** a student or teacher user requests the export endpoint
- **THEN** the system SHALL return HTTP 403 Forbidden

### Requirement: Export with pseudonymization
The system SHALL support a `pseudonymize=true` query parameter that scrubs personally identifiable information from the export.

#### Scenario: Pseudonymized export
- **WHEN** an admin requests with `?pseudonymize=true`
- **THEN** `student_id` SHALL be replaced with `SHA-256(student_id + deployment_salt)`
- **THEN** chat message content in event payloads SHALL be replaced with `"[REDACTED]"`
- **THEN** code content SHALL be replaced with line count metadata only
- **THEN** the response metadata SHALL include `is_pseudonymized: true`

#### Scenario: Non-pseudonymized export
- **WHEN** an admin requests without pseudonymize or with `pseudonymize=false`
- **THEN** all data SHALL be returned with original identifiers and content
