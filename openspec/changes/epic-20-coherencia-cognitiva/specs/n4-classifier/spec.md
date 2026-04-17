## ADDED Requirements

### Requirement: Prompt type classification
The N4Classifier SHALL classify each user message into a prompt_type: exploratory (seeks to understand), verifier (contrasts own hypothesis), or generative (requests code directly). The prompt_type SHALL be returned alongside n4_level and sub_classification.

#### Scenario: Exploratory prompt detected
- **WHEN** a user message contains "cómo funciona", "por qué", "qué pasa si", "explicame"
- **THEN** prompt_type SHALL be "exploratory"

#### Scenario: Verifier prompt detected
- **WHEN** a user message contains "está bien mi", "es correcto", "lo hice bien", "funciona?"
- **THEN** prompt_type SHALL be "verifier"

#### Scenario: Generative prompt detected
- **WHEN** a user message contains "hacé vos", "dame el código", "escribime", "resolvelo"
- **THEN** prompt_type SHALL be "generative"

#### Scenario: Default prompt type
- **WHEN** a user message does not match any prompt_type pattern
- **THEN** prompt_type SHALL be "exploratory" (default)

#### Scenario: Assistant messages have no prompt_type
- **WHEN** role is "assistant"
- **THEN** prompt_type SHALL be None

## MODIFIED Requirements

### Requirement: N4ClassificationResult structure
The N4ClassificationResult dataclass SHALL include n4_level (int 1-4), sub_classification (critical/dependent/exploratory), confidence (high/low), and prompt_type (exploratory/verifier/generative or None).

#### Scenario: User message classification result
- **WHEN** a user message is classified
- **THEN** the result SHALL contain all four fields with prompt_type set

#### Scenario: Assistant message classification result
- **WHEN** an assistant message is classified
- **THEN** the result SHALL contain n4_level, sub_classification, confidence, and prompt_type=None
