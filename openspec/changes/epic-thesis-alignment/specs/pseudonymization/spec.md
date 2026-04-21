## ADDED Requirements

### Requirement: UUID-based pseudonymization documentation
The system SHALL document that UUIDs used for student_id serve as pseudonyms per the thesis requirements. This documentation SHALL be in the codebase (model docstring or inline comment on the field).

#### Scenario: Reviewer audits pseudonymization approach
- **WHEN** a thesis reviewer examines the data model
- **THEN** the `student_id` UUID field SHALL have documentation explaining it functions as a pseudonym
- **THEN** no direct PII (name, email) SHALL be stored in cognitive schema tables

### Requirement: Payload scrubbing for sensitive content
The system SHALL provide a utility function that redacts sensitive fields from cognitive event payloads for research use.

#### Scenario: Scrub chat content from payload
- **WHEN** a payload contains `message_content` or `tutor_response` fields
- **THEN** the scrubbing function SHALL replace their values with `"[REDACTED]"`
- **THEN** all other payload fields SHALL remain unchanged

#### Scenario: Scrub code content from payload
- **WHEN** a payload contains `code` or `snapshot_content` fields
- **THEN** the scrubbing function SHALL replace the value with `{"line_count": N}` where N is the original line count
