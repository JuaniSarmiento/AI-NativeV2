## ADDED Requirements

### Requirement: GET session metrics endpoint
The system SHALL expose `GET /api/v1/cognitive/sessions/{id}/metrics` returning the `CognitiveMetrics` for a given session. Auth: docente (own commission) or admin. Response format: standard `{ status, data, meta, errors }`.

#### Scenario: Metrics exist for session
- **WHEN** a docente requests metrics for a closed session with computed metrics
- **THEN** the system SHALL return 200 with all metric fields in the response body

#### Scenario: Session not found
- **WHEN** the session ID does not exist
- **THEN** the system SHALL return 404

#### Scenario: Metrics not yet computed
- **WHEN** the session exists but is still open (no metrics yet)
- **THEN** the system SHALL return 404 with message indicating metrics are pending

### Requirement: GET teacher dashboard endpoint
The system SHALL expose `GET /api/v1/teacher/courses/{id}/dashboard` with required query param `commission_id`. Auth: docente (own commission) or admin. The endpoint SHALL return aggregated N1-N4 averages, Qe distribution, student count, risk level distribution, and per-student summary. All queries SHALL use `cognitive_sessions.commission_id` directly — zero cross-schema JOINs.

#### Scenario: Dashboard with data
- **WHEN** a docente requests dashboard for a commission with 5 students who have closed sessions
- **THEN** the system SHALL return averages for N1-N4, Qe distribution, risk breakdown, and per-student summaries

#### Scenario: Empty commission
- **WHEN** a commission has no cognitive sessions
- **THEN** the system SHALL return 200 with zero counts and empty aggregations

#### Scenario: Filter by exercise
- **WHEN** query param `exercise_id` is provided
- **THEN** aggregations SHALL only include sessions for that exercise

### Requirement: GET student profile endpoint
The system SHALL expose `GET /api/v1/teacher/students/{id}/profile` returning the cognitive profile for a specific student. Auth: docente (own commission) or admin. The profile SHALL include: latest metrics per exercise, N1-N4 trend over time, overall risk level, and aggregated Qe score.

#### Scenario: Student with multiple sessions
- **WHEN** a student has 3 closed sessions across different exercises
- **THEN** the profile SHALL include metrics for all 3, plus aggregated trends

#### Scenario: Student not found
- **WHEN** the student ID has no cognitive sessions
- **THEN** the system SHALL return 200 with empty metrics (not 404 — the student exists in operational, we just have no cognitive data)

### Requirement: GET student progress endpoint
The system SHALL expose `GET /api/v1/student/me/progress` returning the authenticated student's cognitive progress. Auth: alumno (own data only). The response SHALL include aggregated scores and temporal evolution but SHALL NOT expose individual session details, dependency scores, or risk levels — to prevent gaming.

#### Scenario: Student views own progress
- **WHEN** an alumno requests their progress
- **THEN** the system SHALL return aggregated N1-N4 scores and evolution over time

#### Scenario: Anti-gaming enforcement
- **WHEN** the response is generated
- **THEN** it SHALL NOT include: dependency_score, risk_level, help_seeking_ratio, or per-session breakdowns
