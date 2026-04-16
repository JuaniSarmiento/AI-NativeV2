## ADDED Requirements

### Requirement: N4Classifier classifies user messages by cognitive level
The N4Classifier SHALL analyze the content of a student's message and classify it into N1-N4.

#### Scenario: Student asks basic comprehension question
- **WHEN** the student message contains comprehension patterns
- **THEN** the classifier SHALL return n4_level=1

#### Scenario: Student asks about strategy
- **WHEN** the student message contains strategy patterns
- **THEN** the classifier SHALL return n4_level=2

#### Scenario: Student asks about errors or validation
- **WHEN** the student message contains validation patterns
- **THEN** the classifier SHALL return n4_level=3

#### Scenario: Student evaluates AI interaction critically
- **WHEN** the student message contains metacognitive patterns
- **THEN** the classifier SHALL return n4_level=4

#### Scenario: Ambiguous message defaults to N1
- **WHEN** the student message does not match any pattern
- **THEN** the classifier SHALL default to n4_level=1

### Requirement: N4Classifier classifies assistant messages
The N4Classifier SHALL classify the tutor's response by guidance type.

#### Scenario: Tutor provides comprehension guidance
- **WHEN** the tutor response focuses on understanding the problem
- **THEN** the classifier SHALL return n4_level=1

#### Scenario: Tutor provides validation guidance
- **WHEN** the tutor response helps with debugging
- **THEN** the classifier SHALL return n4_level=3

### Requirement: N4Classifier provides sub-classification
The N4Classifier SHALL sub-classify as critical, exploratory, or dependent.

#### Scenario: Student is stuck
- **WHEN** the student indicates being blocked
- **THEN** the sub-classification SHALL be "critical"

#### Scenario: Student is exploring
- **WHEN** the student asks open-ended questions
- **THEN** the sub-classification SHALL be "exploratory"

#### Scenario: Student depends on tutor
- **WHEN** the student asks for confirmation on every step
- **THEN** the sub-classification SHALL be "dependent"

### Requirement: N4Classifier persists n4_level in tutor_interactions
The classifier result SHALL be written to the n4_level field.

#### Scenario: User turn classified
- **WHEN** a user turn is classified as N2
- **THEN** the TutorInteraction record SHALL have n4_level=2

#### Scenario: Assistant turn classified
- **WHEN** an assistant turn is classified as N3
- **THEN** the TutorInteraction record SHALL have n4_level=3
