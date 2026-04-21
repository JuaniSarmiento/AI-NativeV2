## ADDED Requirements

### Requirement: GP3 guardrail — Reference student's actual code
The guardrails processor SHALL verify that when the tutor's response contains code-related guidance, it references or acknowledges the student's current code state.

#### Scenario: Tutor response references student code
- **WHEN** the tutor response discusses code AND the student has submitted code snapshots
- **THEN** the guardrail SHALL check that the response contains at least one reference to a variable, function, or pattern present in the student's latest code snapshot
- **THEN** if no reference is found, the guardrail SHALL log a `guardrail.gp3_violation` event (audit only, not blocking)

#### Scenario: No student code available
- **WHEN** the student has not yet written any code
- **THEN** the GP3 guardrail SHALL be skipped

### Requirement: GP5 guardrail — Suggest concrete test case
The guardrails processor SHALL verify that when the tutor helps with debugging or validation, it suggests a concrete test case for the student to try.

#### Scenario: Tutor helps with debugging without suggesting test
- **WHEN** the tutor response addresses a code error or debugging scenario AND does not contain a concrete test suggestion (e.g., "probá con el valor X", "¿qué pasa si le pasás [3, 1, 2]?")
- **THEN** the guardrail SHALL log a `guardrail.gp5_violation` event (audit only, not blocking)

#### Scenario: Tutor includes test suggestion
- **WHEN** the tutor response contains a concrete test case or specific input values for the student to try
- **THEN** the GP5 guardrail SHALL pass without logging
