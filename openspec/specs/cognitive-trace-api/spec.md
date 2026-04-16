## ADDED Requirements

### Requirement: Unified trace endpoint
The system SHALL provide `GET /api/v1/cognitive/sessions/{session_id}/trace` returning a unified trace payload containing: session metadata, all CTR events ordered by sequence_number, cognitive metrics (if computed), and hash chain verification result. Requires role docente or admin. Response SHALL follow the standard envelope format.

#### Scenario: Successful trace retrieval
- **WHEN** a docente calls GET `/api/v1/cognitive/sessions/{id}/trace`
- **THEN** the system SHALL return status 200 with session, events, metrics, and verification data in a single response

#### Scenario: Session not found
- **WHEN** the session_id does not exist
- **THEN** the system SHALL return 404

#### Scenario: Open session trace
- **WHEN** a docente requests the trace of an open (not closed) session
- **THEN** the system SHALL return the partial trace with metrics as null and verification as pending

### Requirement: Timeline endpoint
The system SHALL provide `GET /api/v1/cognitive/sessions/{session_id}/timeline` returning CTR events in chronological order with N4 level annotations from the event payload. Supports pagination via `page` and `per_page` query params. Requires role docente or admin.

#### Scenario: Paginated timeline
- **WHEN** a docente calls GET `/api/v1/cognitive/sessions/{id}/timeline?page=1&per_page=50`
- **THEN** the system SHALL return events ordered by created_at ASC with pagination meta

#### Scenario: N4 annotation present
- **WHEN** an event has n4_level in its payload
- **THEN** the timeline response SHALL include n4_level as a top-level field on that event

### Requirement: Code evolution endpoint
The system SHALL provide `GET /api/v1/cognitive/sessions/{session_id}/code-evolution` returning code snapshots associated with the session, ordered chronologically. Each snapshot SHALL include the student code text and timestamp. The endpoint joins cognitive events (type code.snapshot) with operational.code_snapshots via snapshot_id in the event payload. Requires role docente or admin.

#### Scenario: Multiple snapshots
- **WHEN** a session has 3 code.snapshot events
- **THEN** the endpoint SHALL return 3 snapshot entries with code text ordered by timestamp ASC

#### Scenario: No snapshots
- **WHEN** a session has no code.snapshot events
- **THEN** the endpoint SHALL return an empty list

### Requirement: Sessions by commission endpoint
The system SHALL provide `GET /api/v1/cognitive/sessions` with query params `commission_id` (required), `student_id` (optional), `exercise_id` (optional), `status` (optional), `page`, `per_page`. Returns paginated list of cognitive sessions. Requires role docente or admin.

#### Scenario: List sessions for a commission
- **WHEN** a docente calls GET `/api/v1/cognitive/sessions?commission_id={id}`
- **THEN** the system SHALL return all cognitive sessions for that commission ordered by started_at DESC

#### Scenario: Filter by student and exercise
- **WHEN** a docente adds `student_id` and `exercise_id` query params
- **THEN** only sessions matching both filters SHALL be returned
