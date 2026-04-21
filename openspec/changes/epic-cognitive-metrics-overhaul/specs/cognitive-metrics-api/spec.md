## MODIFIED Requirements

### Requirement: Dashboard endpoint response includes coherence and appropriation
The `GET /api/v1/teacher/courses/{id}/dashboard` endpoint SHALL include `latest_temporal_coherence`, `latest_code_discourse`, `latest_inter_iteration`, and `latest_appropriation_type` fields in each StudentSummary.

#### Scenario: Student with computed coherence scores
- **WHEN** dashboard is requested and student has closed sessions with coherence computed
- **THEN** response includes `latest_temporal_coherence: 85.0, latest_code_discourse: 52.0, latest_inter_iteration: 28.0, latest_appropriation_type: "reflexiva"`

#### Scenario: Student without tutor interaction
- **WHEN** student has no tutor.question_asked events
- **THEN** `latest_appropriation_type: "autonomo"` and coherence fields may be null

### Requirement: Dashboard commission averages use per-student latest
The commission aggregate values (avg_n1, avg_n2, avg_n3, avg_n4) SHALL be computed using each student's LATEST session only, not all sessions.

#### Scenario: Equal weight per student
- **WHEN** student A has 10 sessions (latest N1=80) and student B has 1 session (N1=40)
- **THEN** avg_n1 = (80 + 40) / 2 = 60, not weighted by session count

### Requirement: Trace endpoint includes score_breakdown and anomalies
The `GET /api/v1/cognitive/sessions/{id}/trace` response SHALL include a `score_breakdown` object (per-N condition details) and an `anomalies` array (coherence violations detected).

#### Scenario: Session with anomalies
- **WHEN** trace requested for session with `solution_without_comprehension` detected
- **THEN** response includes `anomalies: [{type: "solution_without_comprehension", description: "El alumno entrego sin evidencia de lectura"}]`

#### Scenario: Session without metrics (still open)
- **WHEN** trace requested for open session
- **THEN** `score_breakdown` and `anomalies` are null

## ADDED Requirements

### Requirement: Student evolution endpoint
The API SHALL provide `GET /api/v1/cognitive/students/{student_id}/evolution` with required query param `commission_id`. Returns chronologically ordered session scores.

#### Scenario: Student with 5 sessions in commission
- **WHEN** `GET /api/v1/cognitive/students/{id}/evolution?commission_id=X`
- **THEN** response is `{status: "ok", data: [{session_id, exercise_id, exercise_title, started_at, n1, n2, n3, n4, qe, risk_level}...]}` ordered by started_at ASC

#### Scenario: Student not in commission
- **WHEN** request for student not enrolled in the commission
- **THEN** response returns empty array (not 404)

#### Scenario: Authorization
- **WHEN** request from role=alumno for another student
- **THEN** response is 403 Forbidden

### Requirement: Dashboard StudentSummary includes score_breakdown
Each StudentSummary in the dashboard response SHALL include a `latest_score_breakdown` field containing the breakdown from the latest session.

#### Scenario: Dashboard with breakdown
- **WHEN** dashboard requested
- **THEN** each student entry includes `latest_score_breakdown: {n1: [{condition, met, points}...], ...}`
