## ADDED Requirements

### Requirement: GuardrailsProcessor detects excessive code in LLM response
The GuardrailsProcessor SHALL analyze the complete LLM response text and detect code blocks that exceed the maximum allowed lines.

#### Scenario: Response contains more than 5 lines of code
- **WHEN** the LLM response contains a fenced code block (```) with more than 5 lines of code
- **THEN** the GuardrailsProcessor SHALL flag a violation of type `excessive_code`

#### Scenario: Response contains 5 or fewer lines of code
- **WHEN** the LLM response contains code blocks totaling 5 lines or fewer
- **THEN** the GuardrailsProcessor SHALL NOT flag a violation

#### Scenario: Response contains multiple small code blocks
- **WHEN** the LLM response contains multiple code blocks that individually are <=5 lines but combined exceed 5 lines
- **THEN** the GuardrailsProcessor SHALL flag a violation of type `excessive_code` (total lines across all blocks)

### Requirement: GuardrailsProcessor detects direct solution patterns
The GuardrailsProcessor SHALL detect when the LLM response provides a complete function, class, or solution that directly solves the exercise.

#### Scenario: Response contains a complete function definition
- **WHEN** the LLM response contains a complete function definition (def/function with body) inside a code block
- **THEN** the GuardrailsProcessor SHALL flag a violation of type `direct_solution`

#### Scenario: Response contains partial pseudocode or hints
- **WHEN** the LLM response contains pseudocode, partial snippets, or conceptual hints without complete implementations
- **THEN** the GuardrailsProcessor SHALL NOT flag a violation

### Requirement: GuardrailsProcessor detects non-socratic responses
The GuardrailsProcessor SHALL detect when the LLM response provides direct answers without any socratic questioning or pedagogical guidance.

#### Scenario: Response has no questions and provides direct code
- **WHEN** the LLM response contains code but no interrogative sentences (questions ending in ?)
- **THEN** the GuardrailsProcessor SHALL flag a violation of type `non_socratic`

#### Scenario: Response asks guiding questions alongside explanation
- **WHEN** the LLM response includes questions that guide the student's thinking
- **THEN** the GuardrailsProcessor SHALL NOT flag a violation

### Requirement: GuardrailsProcessor emits guardrail.triggered event
When a violation is detected, the GuardrailsProcessor SHALL emit a `guardrail.triggered` event to the outbox for governance auditing.

#### Scenario: Violation detected during chat
- **WHEN** the GuardrailsProcessor detects any violation type
- **THEN** an EventOutbox record SHALL be created with event_type `guardrail.triggered` and payload containing: interaction_id, student_id, exercise_id, session_id, violation_type, violation_details, and timestamp

#### Scenario: No violation detected
- **WHEN** the GuardrailsProcessor analyzes a response and finds no violations
- **THEN** no outbox event SHALL be emitted

### Requirement: GuardrailsProcessor generates corrective follow-up message
When a violation is detected, the GuardrailsProcessor SHALL generate a corrective message that redirects the student back to the socratic learning process.

#### Scenario: Excessive code violation
- **WHEN** an `excessive_code` violation is detected
- **THEN** the corrective message SHALL acknowledge the previous response was too detailed and redirect with a guiding question

#### Scenario: Direct solution violation
- **WHEN** a `direct_solution` violation is detected
- **THEN** the corrective message SHALL redirect the student to think through the problem step by step

### Requirement: GuardrailsProcessor uses configurable thresholds from guardrails_config
The GuardrailsProcessor SHALL read violation thresholds from the TutorSystemPrompt's guardrails_config JSONB field.

#### Scenario: Custom max_code_lines configured
- **WHEN** guardrails_config contains `{"max_code_lines": 3}`
- **THEN** the GuardrailsProcessor SHALL use 3 as the threshold instead of the default 5

#### Scenario: No guardrails_config set
- **WHEN** the active TutorSystemPrompt has guardrails_config=NULL
- **THEN** the GuardrailsProcessor SHALL use default thresholds (max_code_lines=5)
