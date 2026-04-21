## ADDED Requirements

### Requirement: Filter events by n4_level column instead of event type sets
The MetricsEngine SHALL determine which events belong to each N-level by reading the `n4_level` attribute on each event, NOT by checking membership in hardcoded event type frozensets.

#### Scenario: Event classified as N1 by classifier
- **WHEN** MetricsEngine computes N1 score and an event has `n4_level=1`
- **THEN** that event counts toward N1 regardless of its `event_type` string

#### Scenario: Event with n4_level=None
- **WHEN** an event has `n4_level=None` (lifecycle event)
- **THEN** it SHALL NOT contribute to any N-score calculation

### Requirement: N1 comprehension score requires meaningful reading evidence
The N1 score SHALL NOT give presence points merely for opening an exercise. Reading time above 15 seconds is required for presence, and `code.snapshot` SHALL NOT count as N1.

#### Scenario: Student opens exercise and immediately codes
- **WHEN** student has `reads_problem` but `problem.reading_time` < 15000ms (or absent)
- **THEN** N1 presence component = 0

#### Scenario: Student reads for 20 seconds
- **WHEN** `problem.reading_time` with `reading_duration_ms` >= 15000
- **THEN** N1 presence component = 15 points

#### Scenario: Student reads for 50 seconds
- **WHEN** `problem.reading_time` with `reading_duration_ms` >= 45000
- **THEN** N1 presence component = 30 points (full)

#### Scenario: Student rereads problem after coding
- **WHEN** `problem.reread` event exists in session
- **THEN** N1 depth component gains 15 points

### Requirement: N2 strategy score requires planning evidence
The N2 score SHALL NOT use `submission.created` as presence indicator. Presence requires either `pseudocode.written` OR a tutor question classified as N2.

#### Scenario: Student submits without any planning
- **WHEN** session has `submission.created` but no `pseudocode.written` and no N2 tutor questions
- **THEN** N2 score = 0

#### Scenario: Student writes pseudocode before coding
- **WHEN** `pseudocode.written` event exists
- **THEN** N2 presence component = 20 points

#### Scenario: Student asks strategy question to tutor
- **WHEN** `tutor.question_asked` with `n4_level=2` exists
- **THEN** N2 presence component += 10 points

#### Scenario: Student plans but doesn't submit
- **WHEN** session has `pseudocode.written` and `code.run` but no `submission.created`
- **THEN** N2 score SHALL still be calculated (strategy exists regardless of submission)

### Requirement: N3 validation score distinguishes test quality
The N3 score SHALL award bonus points for `test.manual_case` events, especially edge cases.

#### Scenario: Student writes manual test cases
- **WHEN** `test.manual_case` events exist in session
- **THEN** N3 depth component gains 15 points

#### Scenario: Student tests edge cases
- **WHEN** `test.manual_case` with `is_edge_case=true` exists
- **THEN** N3 quality component gains 15 points

### Requirement: N4 score integrates code acceptance and reformulation
The N4 score SHALL incorporate `code.accepted_from_tutor` and `prompt.reformulated` events.

#### Scenario: Student copies code without modification
- **WHEN** `code.accepted_from_tutor` with `was_modified_after=false` exists AND no subsequent `code.run`
- **THEN** dependency_penalty multiplier increases by 1.5x

#### Scenario: Student reformulates prompts
- **WHEN** `prompt.reformulated` events exist in session
- **THEN** N4 bonus component gains 10 points (replaces diversity bonus if present)

### Requirement: qe_verification measures actual verification behavior
The `qe_verification` sub-score SHALL measure the ratio of code changes followed by test execution, NOT simply count runs.

#### Scenario: Student runs code after each change
- **WHEN** 3 out of 4 code.snapshots are followed by a code.run within the same session
- **THEN** `qe_verification` = 75

#### Scenario: Student makes many changes but only runs once at the end
- **WHEN** 5 code.snapshots exist but only 1 code.run (at the end)
- **THEN** `qe_verification` = 20 (1/5 = low verification discipline)

### Requirement: qe_integration compares against immediately preceding response
The `qe_integration` sub-score SHALL compare each post-tutor run against the MOST RECENT tutor response before it, not against any prior response.

#### Scenario: Run after second tutor response
- **WHEN** tutor_response_1 (seq=5), tutor_response_2 (seq=10), code.run (seq=12)
- **THEN** the run at seq=12 counts as integration of response_2 only

### Requirement: risk_level handles N4=null correctly
When N4 is null (no tutor interaction), the risk derivation SHALL exclude N4 from consideration but still evaluate risk based on N1, N2, N3, and dependency_score.

#### Scenario: Autonomous student with low N1
- **WHEN** N4=null AND N1=15 AND N2=60 AND N3=70
- **THEN** risk level SHALL be triggered by low N1, NOT masked by N4 defaulting to 100

#### Scenario: Autonomous student with all good scores
- **WHEN** N4=null AND N1=80 AND N2=75 AND N3=85
- **THEN** risk level = "low" (N4 absence is not penalized)

### Requirement: N2 quality check requires meaningful diversity
The N2 quality component for "multiple distinct event types" SHALL require at least 3 distinct types that include at least one N2-classified event, not merely 2 types of any kind.

#### Scenario: Session with only reads_problem and submission.created
- **WHEN** only 2 event types exist and neither is classified as N2
- **THEN** diversity quality bonus = 0

### Requirement: Store score breakdown in CognitiveMetrics
The MetricsEngine SHALL produce a `score_breakdown` dict for each N-score documenting which conditions contributed (met/unmet) to the final score. This SHALL be stored as JSONB on the CognitiveMetrics record.

#### Scenario: N1 breakdown stored
- **WHEN** MetricsEngine computes N1=35
- **THEN** `score_breakdown.n1` contains entries like `{condition: "reading_time >= 15s", met: true, points: 15}`, `{condition: "problem.reread", met: false, points: 0}`

### Requirement: Commission AVG uses per-student latest session
The commission aggregate query SHALL compute AVG(N1), AVG(N2), AVG(N3), AVG(N4) using only the LATEST session per student (by computed_at DESC), not all sessions.

#### Scenario: Student A has 10 sessions, Student B has 1 session
- **WHEN** computing commission averages
- **THEN** Student A's latest session and Student B's latest session each contribute equally (weight = 1)
