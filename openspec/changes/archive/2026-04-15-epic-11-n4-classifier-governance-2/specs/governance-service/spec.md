## ADDED Requirements

### Requirement: GovernanceService records policy violations
The GovernanceService SHALL persist governance events when guardrail violations are detected.

#### Scenario: Guardrail triggered event recorded
- **WHEN** TutorService detects a guardrail violation
- **THEN** a GovernanceEvent SHALL be created with event_type="guardrail.triggered"

### Requirement: GovernanceService records prompt lifecycle events
The GovernanceService SHALL record events for prompt creation, activation, and deactivation.

#### Scenario: New prompt creation recorded
- **WHEN** a new TutorSystemPrompt is created
- **THEN** a GovernanceEvent SHALL be created with event_type="prompt.created"

#### Scenario: Prompt activation recorded
- **WHEN** a prompt is activated
- **THEN** a GovernanceEvent SHALL be created with event_type="prompt.activated"

#### Scenario: Prompt deactivation recorded
- **WHEN** a prompt is deactivated
- **THEN** a GovernanceEvent SHALL be created with event_type="prompt.deactivated"

### Requirement: GovernanceService emits governance bus events
The GovernanceService SHALL emit outbox events for downstream consumers.

#### Scenario: Cognitive classified event emitted
- **WHEN** an interaction is classified
- **THEN** an EventOutbox record SHALL be created with event_type="cognitive.classified"

#### Scenario: Governance flag raised event emitted
- **WHEN** a governance event of type guardrail.triggered is recorded
- **THEN** an EventOutbox record SHALL be created with event_type="governance.flag.raised"
