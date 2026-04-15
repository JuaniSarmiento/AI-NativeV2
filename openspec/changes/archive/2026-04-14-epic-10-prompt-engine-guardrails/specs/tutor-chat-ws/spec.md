## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Chat guardrail message type
The WebSocket protocol SHALL support a new outgoing message type `chat.guardrail` for corrective messages when a violation is detected.

#### Scenario: Frontend receives guardrail message
- **WHEN** a guardrail violation is detected after streaming completes
- **THEN** the server SHALL send `{ "type": "chat.guardrail", "violation_type": "excessive_code|direct_solution|non_socratic", "corrective_message": "..." }` after the `chat.done` message
