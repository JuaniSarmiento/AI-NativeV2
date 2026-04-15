## ADDED Requirements

### Requirement: Code execution endpoint
The system SHALL expose `POST /api/v1/student/exercises/{id}/run` accepting `{ code: str }` and returning `{ stdout, stderr, exit_code, runtime_ms, status, test_results: [{ id, description, passed, actual_output, expected_output? }] }`. Only authenticated students can call this endpoint.

#### Scenario: Successful execution with test results
- **WHEN** a student submits valid code for an exercise
- **THEN** the response SHALL include stdout, test results per case, and overall status

#### Scenario: Execution events emitted
- **WHEN** code executes successfully
- **THEN** a `code.executed` event SHALL be written to event_outbox

#### Scenario: Failed execution events emitted
- **WHEN** code fails (timeout, memory, syntax error)
- **THEN** a `code.execution.failed` event SHALL be written to event_outbox

### Requirement: Security — only enrolled students can run
The system SHALL verify that the student is enrolled in the course that owns the exercise before allowing execution.

#### Scenario: Non-enrolled student rejected
- **WHEN** a student not enrolled in the exercise's course tries to run code
- **THEN** the system SHALL return 403
