## MODIFIED Requirements

### Requirement: Chat message flow with N4 classification integrated
The system SHALL classify both user and assistant turns with N4Classifier after guardrails, persisting n4_level and emitting cognitive.classified events.

#### Scenario: Both turns are N4 classified
- **WHEN** a student sends a message and receives a response
- **THEN** both TutorInteraction records SHALL have n4_level set and cognitive.classified events emitted

#### Scenario: Classification adds minimal latency
- **WHEN** the N4Classifier runs post-stream
- **THEN** classification SHALL complete in <5ms (pure heuristic, no I/O)

#### Scenario: Guardrail violations trigger governance events
- **WHEN** GuardrailsProcessor detects a violation
- **THEN** GovernanceService.record_guardrail_violation() SHALL be called and a governance event persisted
