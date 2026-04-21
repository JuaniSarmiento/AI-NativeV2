## MODIFIED Requirements

### Requirement: Hash chain formula includes prompt hash
The CTR hash chain formula SHALL include `prompt_hash` as a dedicated input parameter. Sessions SHALL carry a `chain_version` field to support versioned verification.

#### Scenario: New session uses V2 hash formula
- **WHEN** a new cognitive session is created
- **THEN** the session SHALL be created with `chain_version=2`
- **THEN** event hashes SHALL be computed as `SHA-256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso + ":" + prompt_hash)`
- **THEN** if no prompt_hash is available for the event, an empty string SHALL be used

#### Scenario: Existing sessions verified with V1 formula
- **WHEN** `verify_chain()` is called on a session with `chain_version=1`
- **THEN** the system SHALL use the original formula `SHA-256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso)`

#### Scenario: V2 session verified with V2 formula
- **WHEN** `verify_chain()` is called on a session with `chain_version=2`
- **THEN** the system SHALL use the V2 formula including prompt_hash
