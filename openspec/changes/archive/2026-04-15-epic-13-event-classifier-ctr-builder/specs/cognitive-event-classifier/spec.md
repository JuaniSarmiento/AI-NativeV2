## ADDED Requirements

### Requirement: Classifier transforms raw events to canonical cognitive event types
The classifier SHALL map raw Event Bus event_type to canonical CTR event_type with N4 level.

#### Scenario: reads_problem maps to N1
- **WHEN** raw event reads_problem is received
- **THEN** cognitive event_type SHALL be "reads_problem" with n4_level hint N1

#### Scenario: code.executed maps to code.run N3
- **WHEN** raw event code.executed is received
- **THEN** cognitive event_type SHALL be "code.run" with n4_level hint N3

#### Scenario: tutor.interaction.completed splits by role
- **WHEN** raw event tutor.interaction.completed with role=user is received
- **THEN** cognitive event_type SHALL be "tutor.question_asked" with n4_level hint N4

#### Scenario: exercise.submitted maps to submission.created
- **WHEN** raw event exercise.submitted is received
- **THEN** cognitive event_type SHALL be "submission.created" with n4_level hint N2
