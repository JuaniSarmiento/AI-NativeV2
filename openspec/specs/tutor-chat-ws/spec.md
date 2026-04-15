## ADDED Requirements

### Requirement: WebSocket endpoint for tutor chat
The system SHALL expose a WebSocket endpoint at `ws://api/ws/tutor/chat?token=<JWT>` that accepts connections from authenticated alumnos.

#### Scenario: Successful connection with valid JWT
- **WHEN** an alumno connects with a valid JWT token via query param
- **THEN** the server SHALL accept the WebSocket connection and send `{ "type": "connected" }`

#### Scenario: Rejected connection with invalid JWT
- **WHEN** a client connects with an expired or invalid JWT
- **THEN** the server SHALL close the connection with code 4401 and reason "Invalid token"

#### Scenario: Rejected connection for non-alumno role
- **WHEN** a docente or admin connects to the tutor chat endpoint
- **THEN** the server SHALL close the connection with code 4403 and reason "Forbidden"

### Requirement: Chat message flow with streaming
The system SHALL receive chat messages from the alumno, build contextual prompt via ContextBuilder, stream the tutor's response token-by-token, and apply GuardrailsProcessor post-stream.

#### Scenario: Alumno sends a message and receives streaming response with context
- **WHEN** the alumno sends `{ "type": "chat.message", "content": "...", "exercise_id": "UUID" }`
- **THEN** the server SHALL use ContextBuilder to compose the full prompt (exercise + rubric + student code + base prompt), stream back multiple `{ "type": "chat.token", "content": "..." }` messages followed by `{ "type": "chat.done", "interaction_id": "UUID" }`

#### Scenario: Guardrail violation detected post-stream
- **WHEN** the LLM response triggers a guardrail violation (excessive code, direct solution, or non-socratic)
- **THEN** the server SHALL send `{ "type": "chat.done" }` for the original response, then send a `{ "type": "chat.guardrail", "violation_type": "...", "corrective_message": "..." }` message with a corrective follow-up

#### Scenario: No guardrail violation
- **WHEN** the LLM response passes all guardrail checks
- **THEN** the server SHALL send `{ "type": "chat.done" }` with no additional guardrail message

#### Scenario: Empty message is rejected
- **WHEN** the alumno sends a message with empty or whitespace-only content
- **THEN** the server SHALL respond with `{ "type": "chat.error", "code": "EMPTY_MESSAGE", "message": "..." }`

#### Scenario: Invalid exercise_id is rejected
- **WHEN** the alumno sends a message with an exercise_id that does not exist or they are not enrolled in the course
- **THEN** the server SHALL respond with `{ "type": "chat.error", "code": "INVALID_EXERCISE", "message": "..." }`

### Requirement: Heartbeat protocol
The system SHALL implement ping/pong heartbeat for connection health detection.

#### Scenario: Server responds to client ping
- **WHEN** the client sends `{ "type": "ping" }`
- **THEN** the server SHALL respond with `{ "type": "pong" }`

#### Scenario: Server detects stale connection
- **WHEN** no message is received from the client for 60 seconds
- **THEN** the server SHALL close the connection with code 4408 and reason "Timeout"

### Requirement: Rate limiting per alumno per exercise
The system SHALL enforce a limit of 30 messages per hour per alumno per exercise using a Redis sliding window.

#### Scenario: Message within rate limit
- **WHEN** an alumno sends a message and has sent fewer than 30 in the last hour for that exercise
- **THEN** the message SHALL be processed and the response SHALL include `{ "type": "rate_limit", "remaining": N, "reset_at": "ISO8601" }`

#### Scenario: Message exceeds rate limit
- **WHEN** an alumno sends a message and has already sent 30 in the last hour for that exercise
- **THEN** the server SHALL respond with `{ "type": "chat.error", "code": "RATE_LIMITED", "message": "...", "reset_at": "ISO8601" }` and NOT call the LLM

### Requirement: Session history REST fallback
The system SHALL expose `GET /api/v1/tutor/sessions/{exercise_id}/messages` to retrieve the current session's message history.

#### Scenario: Retrieve recent messages
- **WHEN** an authenticated alumno requests their message history for an exercise
- **THEN** the system SHALL return the last 50 messages of the most recent session, ordered chronologically, with pagination support for older messages

#### Scenario: No session exists
- **WHEN** an alumno requests history for an exercise they haven't chatted about
- **THEN** the system SHALL return an empty list with 200 status

### Requirement: Chat guardrail message type
The WebSocket protocol SHALL support a new outgoing message type `chat.guardrail` for corrective messages when a violation is detected.

#### Scenario: Frontend receives guardrail message
- **WHEN** a guardrail violation is detected after streaming completes
- **THEN** the server SHALL send `{ "type": "chat.guardrail", "violation_type": "excessive_code|direct_solution|non_socratic", "corrective_message": "..." }` after the `chat.done` message
