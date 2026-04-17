## REMOVED Requirements

### Requirement: Emission of cognitive.classified events
**Reason**: The cognitive.classified events emitted by TutorService are redundant — the n4_level already travels in the payload of tutor.interaction.completed. The events:cognitive stream has no consumer, so these events are lost. Removing eliminates dead code and confusion.
**Migration**: The n4_level, sub_classification, and prompt_type are now included directly in the tutor.interaction.completed event payload.

## MODIFIED Requirements

### Requirement: tutor.interaction.completed payload includes prompt_type
The tutor.interaction.completed outbox event payload SHALL include prompt_type (exploratory/verifier/generative/null) alongside the existing n4_level and sub_classification fields.

#### Scenario: User turn event includes prompt_type
- **WHEN** a tutor.interaction.completed event is emitted for a user turn
- **THEN** the payload SHALL include prompt_type from the N4Classifier result

#### Scenario: Assistant turn event has null prompt_type
- **WHEN** a tutor.interaction.completed event is emitted for an assistant turn
- **THEN** the payload SHALL include prompt_type=null

### Requirement: TutorService emits tutor.interaction.completed for user turn
The TutorService SHALL emit a tutor.interaction.completed outbox event for the user turn (not just the assistant turn), so the consumer receives both turns via the event bus.

#### Scenario: Both turns produce outbox events
- **WHEN** a chat turn completes (user message + assistant response)
- **THEN** TWO tutor.interaction.completed events SHALL be written to the outbox — one with role=user and one with role=assistant
