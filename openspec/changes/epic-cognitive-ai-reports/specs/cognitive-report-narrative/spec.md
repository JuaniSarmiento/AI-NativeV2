## ADDED Requirements

### Requirement: Generate Markdown narrative from StructuredAnalysis
The system SHALL send the StructuredAnalysis JSON to the docente's configured LLM (via AI Gateway) with a pedagogical system prompt and return a Markdown narrative report.

#### Scenario: Successful narrative generation
- **WHEN** narrative engine receives a valid StructuredAnalysis and the docente has a valid LLM config
- **THEN** the LLM is called with the system prompt + analysis JSON and the response Markdown is returned

#### Scenario: Docente has no LLM config
- **WHEN** narrative engine is invoked but the requesting docente has no LLMConfig record
- **THEN** the system raises a 422 error with message indicating LLM configuration is required

#### Scenario: LLM API key is invalid or expired
- **WHEN** the LLM adapter raises an authentication error
- **THEN** the system returns a 422 error with a clear message about invalid API key

### Requirement: Narrative follows standardized sections
The system prompt SHALL instruct the LLM to produce a report with exactly these sections: Resumen Ejecutivo, Fortalezas, Áreas de Mejora, Evolución Observada, Recomendaciones Pedagógicas.

#### Scenario: Report structure verification
- **WHEN** a narrative is generated successfully
- **THEN** the Markdown output contains headers for each of the 5 required sections

### Requirement: LLM cannot fabricate evidence
The system prompt SHALL explicitly instruct the LLM to only cite evidence present in the StructuredAnalysis JSON and never invent data, scores, or quotes not provided.

#### Scenario: Prompt includes anti-hallucination instruction
- **WHEN** the system prompt is constructed
- **THEN** it contains an explicit instruction prohibiting the invention of data not present in the input
