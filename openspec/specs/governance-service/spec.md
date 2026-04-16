## Purpose
Domain service for recording governance events: policy violations, prompt lifecycle, bus event emission.

## Requirements

### Requirement: Records policy violations
GovernanceService SHALL persist events for guardrail violations.

#### Scenario: Guardrail triggered
- **WHEN** TutorService detects a violation
- **THEN** GovernanceEvent created with event_type="guardrail.triggered"

### Requirement: Records prompt lifecycle
GovernanceService SHALL record prompt creation, activation, deactivation.

#### Scenario: Prompt created
- **WHEN** new prompt seeded
- **THEN** event_type="prompt.created" with name, version, sha256_hash

#### Scenario: Prompt activated
- **WHEN** prompt activated
- **THEN** event_type="prompt.activated" with old_hash, new_hash

#### Scenario: Prompt deactivated
- **WHEN** prompt deactivated
- **THEN** event_type="prompt.deactivated"

### Requirement: Emits bus events
GovernanceService SHALL emit outbox events for Fase 3.

#### Scenario: cognitive.classified emitted
- **WHEN** interaction classified
- **THEN** EventOutbox with event_type="cognitive.classified"

#### Scenario: governance.flag.raised emitted
- **WHEN** guardrail violation recorded
- **THEN** EventOutbox with event_type="governance.flag.raised"
