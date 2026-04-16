## ADDED Requirements

### Requirement: Session detail endpoint
GET /api/v1/cognitive/sessions/{id} SHALL return session with events.

#### Scenario: Session with events returned
- **WHEN** a valid session ID is requested
- **THEN** the system SHALL return session metadata + all cognitive events ordered by sequence_number

#### Scenario: Session not found
- **WHEN** an invalid session ID is requested
- **THEN** the system SHALL return 404

### Requirement: Hash chain verification endpoint
GET /api/v1/cognitive/sessions/{id}/verify SHALL verify integrity.

#### Scenario: Valid chain
- **WHEN** all hashes match
- **THEN** the system SHALL return { valid: true, events_checked: N }

#### Scenario: Tampered chain
- **WHEN** a hash mismatch is found
- **THEN** the system SHALL return { valid: false, failed_at_sequence: N, expected_hash: "...", actual_hash: "..." }
