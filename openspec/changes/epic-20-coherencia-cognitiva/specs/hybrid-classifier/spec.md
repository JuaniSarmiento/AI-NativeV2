## ADDED Requirements

### Requirement: Hybrid classification in consumer
The CognitiveEventConsumer SHALL use a hybrid classification strategy: regex first, and if confidence is LOW for tutor.interaction.completed events, escalate to an LLM call before persisting the event in the CTR.

#### Scenario: High confidence regex classification
- **WHEN** a tutor.interaction.completed event arrives AND the regex classifier returns confidence=HIGH
- **THEN** the event SHALL be persisted with the regex n4_level without calling the LLM

#### Scenario: Low confidence triggers LLM classification
- **WHEN** a tutor.interaction.completed event arrives AND the regex classifier returns confidence=LOW
- **THEN** the consumer SHALL call the LLM classifier with a 3-second timeout
- **AND** persist the event with the LLM-provided n4_level

#### Scenario: LLM timeout falls back to regex
- **WHEN** the LLM classifier does not respond within 3 seconds
- **THEN** the event SHALL be persisted with the regex n4_level as fallback

#### Scenario: LLM error falls back to regex
- **WHEN** the LLM classifier raises an exception
- **THEN** the event SHALL be persisted with the regex n4_level AND the error SHALL be logged

### Requirement: LLM classification prompt
The LLM classification call SHALL use a minimal prompt (~100 tokens) that provides the message content and asks for a single integer n4_level (1-4) and a prompt_type (exploratory/verifier/generative). The model SHALL be the configured tutor LLM (Mistral small or equivalent).

#### Scenario: LLM returns valid classification
- **WHEN** the LLM returns a valid JSON with n4_level in [1,4] and prompt_type in [exploratory, verifier, generative]
- **THEN** both values SHALL be used in the event payload

#### Scenario: LLM returns invalid format
- **WHEN** the LLM returns a response that cannot be parsed
- **THEN** the consumer SHALL fall back to regex classification and log a warning

### Requirement: Classification happens before CTR persistence
The hybrid classification MUST complete before the event is added to the CTR hash chain. The n4_level in the persisted payload SHALL be the final classified value.

#### Scenario: Hash chain integrity after hybrid classification
- **WHEN** an event is classified via LLM and persisted in the CTR
- **THEN** verify_chain() SHALL return valid=True (the hash includes the final n4_level)
