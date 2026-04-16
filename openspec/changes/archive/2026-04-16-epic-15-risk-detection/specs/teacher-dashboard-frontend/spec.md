## MODIFIED Requirements

### Requirement: Student scores table
The system SHALL display a table of students with columns: Nombre, N1, N2, N3, N4, Qe, Riesgo. The table SHALL support sorting by any score column and filtering by risk level. Each student row SHALL include a risk badge next to the student name showing their latest risk_level with color coding (green/yellow/orange/red) derived from the risk assessments data.

#### Scenario: Sort by risk level
- **WHEN** a docente clicks the "Riesgo" column header
- **THEN** students SHALL be sorted by risk level (critical first)

#### Scenario: Filter by exercise
- **WHEN** a docente selects an exercise from the filter dropdown
- **THEN** the table and radar chart SHALL update to show metrics for that exercise only

#### Scenario: Risk badge display
- **WHEN** a student has a risk assessment with risk_level "high"
- **THEN** a badge with text "Alto" and orange color (--color-warning-700) SHALL appear next to their name in the table

#### Scenario: No risk assessment
- **WHEN** a student has no risk assessment
- **THEN** no risk badge SHALL be displayed (not a "Bajo" badge)

### Requirement: Teacher dashboard page
The system SHALL provide a teacher dashboard page at route `/teacher/courses/:courseId/dashboard`. The page SHALL include a commission selector, N1-N4 radar chart (Recharts), student table with scores and risk badges, risk alerts table section, filter controls, and a "Evaluar Riesgo" button that triggers manual assessment. Design: minimalist UI with the project's design system tokens.

#### Scenario: Dashboard loads with commission selected
- **WHEN** a docente navigates to the dashboard and selects a commission
- **THEN** the page SHALL display: radar chart with N1-N4 commission averages, student table with individual scores and risk badges, risk distribution card, and risk alerts table

#### Scenario: Commission selector
- **WHEN** the page loads
- **THEN** a commission dropdown SHALL be populated from the course's commissions and auto-select the first one

#### Scenario: Manual assessment trigger
- **WHEN** a docente clicks "Evaluar Riesgo"
- **THEN** the system SHALL call POST `/api/v1/teacher/commissions/{id}/risks/assess` and refresh the risk data
