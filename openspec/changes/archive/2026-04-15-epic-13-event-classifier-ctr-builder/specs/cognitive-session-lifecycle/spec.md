## ADDED Requirements

### Requirement: Session created on first event
A cognitive session SHALL be created when the first event arrives for a (student_id, exercise_id) pair without an open session.

#### Scenario: First event creates session
- **WHEN** reads_problem arrives and no open session exists
- **THEN** a new CognitiveSession SHALL be created with status=open

#### Scenario: Event for existing open session reuses it
- **WHEN** an event arrives and an open session exists for that student+exercise
- **THEN** the event SHALL be added to the existing session

### Requirement: Session closes on submission or timeout
Sessions SHALL close when the exercise is submitted or after 30 minutes of inactivity.

#### Scenario: Submission closes session
- **WHEN** exercise.submitted event is received for an open session
- **THEN** the session status SHALL change to closed and session_hash computed

#### Scenario: Timeout closes session
- **WHEN** an open session has no events for 30 minutes
- **THEN** the session SHALL be closed automatically

### Requirement: Session invalidated on hash chain failure
If hash chain verification fails, the session SHALL be marked invalidated.

#### Scenario: Invalid hash detected
- **WHEN** verification detects a hash mismatch
- **THEN** session status SHALL change to invalidated
