## ADDED Requirements

### Requirement: Teacher dashboard page
The system SHALL provide a teacher dashboard page at route `/teacher/courses/:courseId/dashboard`. The page SHALL include a commission selector, N1-N4 radar chart (Recharts), student table with scores, and filter controls. Design: minimalist UI with the project's design system tokens.

#### Scenario: Dashboard loads with commission selected
- **WHEN** a docente navigates to the dashboard and selects a commission
- **THEN** the page SHALL display: radar chart with N1-N4 commission averages, student table with individual scores, and risk level distribution

#### Scenario: Commission selector
- **WHEN** the page loads
- **THEN** a commission dropdown SHALL be populated from the course's commissions and auto-select the first one

### Requirement: N1-N4 radar chart
The system SHALL render a radar chart using Recharts showing N1 (Comprensión), N2 (Estrategia), N3 (Validación), N4 (Interacción IA) scores. The chart SHALL support both commission averages and individual student overlay.

#### Scenario: Commission average radar
- **WHEN** commission data loads
- **THEN** a radar chart SHALL display the 4 N-level averages with Spanish labels

#### Scenario: Student overlay on radar
- **WHEN** a docente clicks a student row in the table
- **THEN** the radar chart SHALL overlay that student's scores on top of the commission average

### Requirement: Student scores table
The system SHALL display a table of students with columns: Nombre, N1, N2, N3, N4, Qe, Riesgo. The table SHALL support sorting by any score column and filtering by risk level.

#### Scenario: Sort by risk level
- **WHEN** a docente clicks the "Riesgo" column header
- **THEN** students SHALL be sorted by risk level (critical first)

#### Scenario: Filter by exercise
- **WHEN** a docente selects an exercise from the filter dropdown
- **THEN** the table and radar chart SHALL update to show metrics for that exercise only

### Requirement: Risk level distribution
The system SHALL display a summary card showing the distribution of risk levels (low/medium/high/critical) as counts and visual indicators.

#### Scenario: Distribution display
- **WHEN** commission data loads
- **THEN** risk level counts SHALL be displayed with color-coded indicators (green/yellow/orange/red)
