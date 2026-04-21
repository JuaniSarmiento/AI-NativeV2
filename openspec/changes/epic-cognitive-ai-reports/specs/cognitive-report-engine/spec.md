## ADDED Requirements

### Requirement: Analytical engine produces StructuredAnalysis
The system SHALL aggregate all closed cognitive sessions for a given student+activity pair and produce a `StructuredAnalysis` JSON object containing overall scores, detected patterns, strengths, weaknesses, evolution trends, and anomalies.

#### Scenario: Student has multiple closed sessions in activity
- **WHEN** analytical engine is invoked for student X and activity Y which has 3 closed sessions
- **THEN** the StructuredAnalysis contains averaged N1-N4 scores, patterns detected across all 3 sessions, and evolution data comparing first to last session

#### Scenario: Student has no closed sessions
- **WHEN** analytical engine is invoked for student X and activity Y which has 0 closed sessions
- **THEN** the engine raises a validation error indicating insufficient data

### Requirement: Pattern detection from CTR events
The system SHALL detect behavioral patterns including: high AI dependency (excessive tutor questions before coding), low validation (few test runs before submission), copy-paste from tutor (code.accepted_from_tutor events), and rapid comprehension (short time from reads_problem to first code.edit).

#### Scenario: High AI dependency detected
- **WHEN** a student asked the tutor more than 8 times before producing code in a session
- **THEN** a pattern of type "high_ai_dependency" with severity "warning" is included in StructuredAnalysis with the exact count as evidence

#### Scenario: No validation behavior detected
- **WHEN** a student submitted code without any preceding test.run or code.run events
- **THEN** a pattern of type "low_validation" with severity "warning" is included with evidence citing the submission without prior execution

### Requirement: Evidence extraction with concrete references
The system SHALL include concrete evidence for every pattern, strength, and weakness — referencing specific event counts, timestamps, metric values, or chat excerpts.

#### Scenario: Strength with metric evidence
- **WHEN** a student's N1 score is above 0.75 across sessions
- **THEN** the strength entry includes the exact average score and comparison text (e.g., "N1 promedio: 0.82")

### Requirement: Data hash for cache invalidation
The system SHALL compute a SHA-256 hash of the StructuredAnalysis JSON (sorted keys, deterministic serialization) to enable cache lookup.

#### Scenario: Same data produces same hash
- **WHEN** the analytical engine is run twice with no new sessions closed between runs
- **THEN** both runs produce identical data_hash values
