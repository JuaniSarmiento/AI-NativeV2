## Purpose
Heuristic classifier for tutor interactions — assigns N4 cognitive level (1-4) and sub-classification per message.

## Requirements

### Requirement: N4Classifier classifies user messages by cognitive level
The N4Classifier SHALL classify student messages into N1 (comprehension), N2 (strategy), N3 (validation), N4 (AI interaction).

#### Scenario: Comprehension question → N1
- **WHEN** the student message contains comprehension patterns
- **THEN** the classifier SHALL return n4_level=1

#### Scenario: Strategy question → N2
- **WHEN** the student message contains strategy patterns
- **THEN** the classifier SHALL return n4_level=2

#### Scenario: Validation/debugging → N3
- **WHEN** the student message contains error/validation patterns
- **THEN** the classifier SHALL return n4_level=3

#### Scenario: Metacognitive evaluation → N4
- **WHEN** the student message evaluates AI interaction critically
- **THEN** the classifier SHALL return n4_level=4

#### Scenario: Ambiguous defaults to N1
- **WHEN** no pattern matches
- **THEN** the classifier SHALL default to n4_level=1

### Requirement: N4Classifier classifies assistant messages
The classifier SHALL also classify tutor responses by guidance type provided.

#### Scenario: Comprehension guidance → N1
- **WHEN** the tutor helps understand the problem
- **THEN** the classifier SHALL return n4_level=1

#### Scenario: Validation guidance → N3
- **WHEN** the tutor helps with debugging
- **THEN** the classifier SHALL return n4_level=3

### Requirement: N4Classifier provides sub-classification
Sub-classification: critical (stuck), exploratory (open questions), dependent (needs confirmation).

#### Scenario: Critical
- **WHEN** the student indicates being blocked
- **THEN** sub_classification SHALL be "critical"

#### Scenario: Exploratory
- **WHEN** the student explores options
- **THEN** sub_classification SHALL be "exploratory"

#### Scenario: Dependent
- **WHEN** the student asks for confirmation on every step
- **THEN** sub_classification SHALL be "dependent"

### Requirement: N4Classifier persists n4_level
The result SHALL be written to tutor_interactions.n4_level (SMALLINT 1-4).

#### Scenario: Both turns classified
- **WHEN** a chat interaction completes
- **THEN** both user and assistant TutorInteraction records SHALL have n4_level set
