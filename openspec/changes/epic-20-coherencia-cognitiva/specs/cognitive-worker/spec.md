## MODIFIED Requirements

### Requirement: Consumer reads n4_level from payload for tutor events
The CognitiveEventClassifier SHALL read the n4_level from the event payload for tutor.interaction.completed events instead of hardcoding N4=4. The payload contains the fine-grained n4_level (1-4) classified by the N4Classifier in the TutorService.

#### Scenario: Tutor event with N1 level in payload
- **WHEN** a tutor.interaction.completed event arrives with payload.n4_level=1
- **THEN** the CognitiveEvent SHALL be persisted with n4_level=1 in its payload, not 4

#### Scenario: Tutor event without n4_level in payload
- **WHEN** a tutor.interaction.completed event arrives without n4_level in payload
- **THEN** the CognitiveEvent SHALL fall back to n4_level=4 (legacy behavior)

### Requirement: Consumer integrates hybrid classifier
The CognitiveEventConsumer SHALL integrate the hybrid classification strategy for tutor.interaction.completed events with LOW confidence regex classification.

#### Scenario: Hybrid classification in consumer pipeline
- **WHEN** a tutor.interaction.completed event arrives with payload containing message content
- **THEN** the consumer SHALL first attempt regex classification, then escalate to LLM if confidence is LOW, before calling add_event()

### Requirement: Consumer rejects events with invalid commission_id
The CognitiveEventConsumer SHALL NOT create sessions with a zero-UUID commission_id. If commission_id cannot be resolved, the event SHALL be logged and discarded.

#### Scenario: Event without valid commission_id
- **WHEN** an event arrives without a commission_id or with "00000000-0000-0000-0000-000000000000"
- **THEN** the event SHALL be logged as a warning and NOT persisted in the CTR
