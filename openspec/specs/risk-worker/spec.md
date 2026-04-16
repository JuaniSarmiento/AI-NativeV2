## ADDED Requirements

### Requirement: RiskWorker service
The system SHALL provide a `RiskWorker` service class in `app/features/risk/service.py` that analyzes accumulated CognitiveMetrics for a student within a commission and produces a RiskAssessment. The worker SHALL be a pure domain service with no FastAPI imports, receiving repositories via constructor injection.

#### Scenario: Automatic assessment after session close
- **WHEN** `assess_student(student_id, commission_id, triggered_by="automatic")` is called
- **THEN** the worker SHALL query all CognitiveMetrics for the student's sessions in that commission, compute risk factors, determine risk_level, generate a recommendation, and upsert a RiskAssessment

#### Scenario: Manual assessment triggered by docente
- **WHEN** `assess_student(student_id, commission_id, triggered_by="manual")` is called
- **THEN** the worker SHALL perform the same analysis but with `triggered_by="manual"`

### Requirement: Dependency factor detection
The system SHALL detect dependency risk when a student's average `dependency_score` across recent sessions (last 5) exceeds 0.5. The factor SHALL be stored in `risk_factors` as `{"dependency": {"score": <avg>, "sessions_above_threshold": <count>, "threshold": 0.5}}`.

#### Scenario: High dependency detected
- **WHEN** a student has 3 out of 5 recent sessions with dependency_score > 0.5 and average dependency_score is 0.6
- **THEN** `risk_factors` SHALL include a "dependency" key with score 0.6 and sessions_above_threshold 3

#### Scenario: No dependency risk
- **WHEN** a student's average dependency_score is 0.3
- **THEN** `risk_factors` SHALL NOT include a "dependency" key

### Requirement: Disengagement factor detection
The system SHALL detect disengagement risk when a student has fewer than 2 cognitive sessions in the last 7 days for a given commission. The factor SHALL be stored as `{"disengagement": {"score": <0-1>, "recent_sessions": <count>, "expected_minimum": 2}}`.

#### Scenario: Disengaged student
- **WHEN** a student has 0 sessions in the last 7 days
- **THEN** `risk_factors` SHALL include "disengagement" with score 1.0

#### Scenario: Active student
- **WHEN** a student has 3 sessions in the last 7 days
- **THEN** `risk_factors` SHALL NOT include a "disengagement" key

### Requirement: Stagnation factor detection
The system SHALL detect stagnation risk when a student's N1-N4 scores show no improvement or decline across their last 3 sessions. Trend is computed as the slope of scores over time.

#### Scenario: Declining scores
- **WHEN** a student's average N-score trend is negative across 3 sessions
- **THEN** `risk_factors` SHALL include "stagnation" with a score proportional to the decline and `trend: "declining"`

#### Scenario: Improving scores
- **WHEN** a student's average N-score trend is positive
- **THEN** `risk_factors` SHALL NOT include a "stagnation" key

### Requirement: Risk level computation
The system SHALL compute `risk_level` from the detected factors: `critical` if any factor score >= 0.8 or 2+ factors present with scores >= 0.6; `high` if any factor score >= 0.6; `medium` if any factor score >= 0.4; `low` otherwise.

#### Scenario: Critical risk
- **WHEN** dependency factor score is 0.85
- **THEN** risk_level SHALL be "critical"

#### Scenario: High risk from combined factors
- **WHEN** dependency score is 0.65 and disengagement score is 0.7
- **THEN** risk_level SHALL be "critical" (2+ factors >= 0.6)

#### Scenario: Low risk
- **WHEN** no factors are detected
- **THEN** risk_level SHALL be "low"

### Requirement: Recommendation generation
The system SHALL generate a human-readable recommendation string in Spanish based on the detected risk factors. The recommendation SHALL be concise (1-3 sentences) and actionable for the docente.

#### Scenario: Dependency recommendation
- **WHEN** dependency factor is detected
- **THEN** recommendation SHALL mention that the student shows high dependency on AI assistance and suggest encouraging autonomous problem-solving

#### Scenario: Multiple factors recommendation
- **WHEN** both dependency and stagnation are detected
- **THEN** recommendation SHALL address both factors in a combined message

### Requirement: Idempotent execution
The system SHALL be idempotent — running the worker twice for the same student/commission on the same day SHALL produce exactly one RiskAssessment row (upsert).

#### Scenario: Double execution
- **WHEN** `assess_student` is called twice for the same student/commission on the same day
- **THEN** exactly one RiskAssessment SHALL exist for that day, with the latest computed values
