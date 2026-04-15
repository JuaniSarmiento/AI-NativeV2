## ADDED Requirements

### Requirement: Tutor events emitted to Event Bus
The system SHALL emit events to the `events:tutor` Redis Stream via the event outbox for every significant tutor interaction.

#### Scenario: tutor.session.started on first message
- **WHEN** an alumno sends their first message for an exercise in a new session
- **THEN** a `tutor.session.started` event SHALL be written to event_outbox with payload `{ student_id, exercise_id, session_id, timestamp }`

#### Scenario: tutor.interaction.completed after each turn
- **WHEN** the tutor completes a response
- **THEN** a `tutor.interaction.completed` event SHALL be written to event_outbox with payload `{ interaction_id, student_id, exercise_id, session_id, role, n4_classification, prompt_hash, tokens_used, timestamp }`

#### Scenario: tutor.session.ended on disconnect or timeout
- **WHEN** the alumno disconnects or the session times out
- **THEN** a `tutor.session.ended` event SHALL be written to event_outbox with payload `{ student_id, exercise_id, session_id, message_count, timestamp }`

### Requirement: Event payload follows standard structure
All tutor events SHALL follow the standard EventBus payload structure defined in event-bus-core.

#### Scenario: Event has standard envelope
- **WHEN** a tutor event is published
- **THEN** it SHALL include `event_id` (UUID), `event_type` (string), `timestamp` (ISO 8601 UTC), `source: "tutor"`, and `data` (domain payload)
