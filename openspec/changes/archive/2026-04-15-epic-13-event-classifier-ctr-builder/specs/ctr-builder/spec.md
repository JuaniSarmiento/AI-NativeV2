## ADDED Requirements

### Requirement: CTR Builder creates hash-chained events
The CTR Builder SHALL compute SHA-256 hashes for each event chained to the previous.

#### Scenario: Genesis hash computed at session creation
- **WHEN** a new cognitive session is created
- **THEN** genesis_hash SHALL be SHA256("GENESIS:" + session_id + ":" + started_at_iso)

#### Scenario: Event hash chains to previous
- **WHEN** a new cognitive event is added to a session
- **THEN** event_hash SHALL be SHA256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso)

#### Scenario: Session hash set at close
- **WHEN** a session is closed
- **THEN** session_hash SHALL be set to the last event's event_hash

### Requirement: Hash chain is verifiable
The system SHALL verify the integrity of a session's hash chain.

#### Scenario: Valid chain passes verification
- **WHEN** all events are recalculated and match stored hashes
- **THEN** verification SHALL return valid=true

#### Scenario: Tampered event detected
- **WHEN** an event's payload was modified after creation
- **THEN** verification SHALL return valid=false with the tampered event identified
