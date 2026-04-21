## MODIFIED Requirements

### Requirement: MetricsEngine computation approach
The MetricsEngine SHALL compute N1-N4 scores by filtering events using the `n4_level` attribute on each event object, not by checking event_type membership in static frozensets. The frozensets `_N1_EVENT_TYPES`, `_N2_EVENT_TYPES`, `_N3_EVENT_TYPES` SHALL be removed.

#### Scenario: New event type classified as N2
- **WHEN** a `pseudocode.written` event has `n4_level=2`
- **THEN** MetricsEngine counts it toward N2 score without any code change to MetricsEngine

#### Scenario: code.snapshot with n4_level=None
- **WHEN** `code.snapshot` event has `n4_level=None`
- **THEN** it does NOT contribute to any N-score

### Requirement: N1 comprehension scoring formula
N1 SHALL be computed as: Presence (30 pts: reading_time thresholds) + Depth (30 pts: reread + N1 tutor questions) + Quality (40 pts: first event not code.run + exploratory N1 question + reflection with difficulty).

#### Scenario: Student with minimal reading
- **WHEN** reading_time < 15s, no reread, no N1 questions
- **THEN** N1 = 0 (no presence points awarded)

#### Scenario: Student with thorough reading and questions
- **WHEN** reading_time >= 45s, reread exists, N1 tutor question exists, first event != code.run
- **THEN** N1 = 30 + 30 + 35 = 95

### Requirement: N2 strategy scoring formula
N2 SHALL be computed as: Presence (30 pts: pseudocode +20, strategy question +10) + Depth (30 pts: N2 question precedes code.run +15, multiple N2 question types +15) + Quality (40 pts: code.run after pseudocode +20, incremental snapshots +20).

#### Scenario: Student who only submits
- **WHEN** session has submission.created but no pseudocode, no N2 questions
- **THEN** N2 = 0

#### Scenario: Student with pseudocode and strategy questions
- **WHEN** pseudocode.written exists AND tutor question N2 precedes first code.run
- **THEN** N2 presence = 30, depth >= 15

### Requirement: Qe verification sub-score formula
`qe_verification` SHALL measure the ratio of code.snapshots that are followed by a code.run within the same session. Formula: `(snapshots_followed_by_run / total_snapshots) * 100`.

#### Scenario: 3 snapshots, 2 followed by runs
- **WHEN** 3 code.snapshots exist and 2 are followed by code.run events
- **THEN** `qe_verification` = 66.67

#### Scenario: No snapshots
- **WHEN** no code.snapshot events exist
- **THEN** `qe_verification` = None

### Requirement: Qe integration sub-score uses nearest preceding response
`qe_integration` SHALL attribute each post-tutor code.run to the most recent tutor response that precedes it by sequence_number, not to any arbitrary prior response.

#### Scenario: Two responses, one run after each
- **WHEN** response_1 (seq=5), run_1 (seq=7), response_2 (seq=10), run_2 (seq=12)
- **THEN** run_1 is attributed to response_1, run_2 is attributed to response_2

### Requirement: Risk level with null N4
When N4 is null, `_derive_risk_level` SHALL compute risk using only N1, N2, N3, and dependency_score. N4 SHALL NOT default to any value — it is simply excluded from the evaluation.

#### Scenario: N4 null with low N1
- **WHEN** N4=null, N1=10, N2=50, N3=60, dependency=0
- **THEN** risk_level evaluates based on min(N1,N2,N3)=10, which triggers high/critical depending on threshold

### Requirement: MetricsEngine outputs score_breakdown
The `compute()` method SHALL return a `score_breakdown` dict alongside the scores, documenting each condition evaluated and its contribution.

#### Scenario: Full computation
- **WHEN** MetricsEngine.compute() runs for a session
- **THEN** result includes `score_breakdown` with per-dimension arrays of `{condition: str, met: bool, points: Decimal}`
