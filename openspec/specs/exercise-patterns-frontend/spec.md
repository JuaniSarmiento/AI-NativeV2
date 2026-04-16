## ADDED Requirements

### Requirement: Exercise patterns page
The system SHALL provide a page at route `/teacher/courses/:courseId/exercises/:exerciseId/patterns` showing aggregated patterns of how a class resolved an exercise. Requires role docente or admin.

#### Scenario: Navigation to patterns
- **WHEN** a docente clicks "Ver patrones" on an exercise
- **THEN** the browser SHALL navigate to the patterns page

### Requirement: Strategy distribution
The system SHALL display the distribution of N2 (strategy) scores across all students who attempted the exercise, as a bar chart or histogram. Labels SHALL be in Spanish.

#### Scenario: Distribution renders
- **WHEN** the patterns page loads with session data
- **THEN** a chart SHALL show how many students scored in each N2 range (0-25, 25-50, 50-75, 75-100)

### Requirement: Error patterns summary
The system SHALL display common N3 (validation) patterns: percentage of students with high error rates (success_efficiency < 50), average number of code runs, and distribution of risk levels.

#### Scenario: Error patterns render
- **WHEN** the patterns page loads
- **THEN** summary cards SHALL show: avg code runs, % students with low success efficiency, risk level distribution

### Requirement: Session list for exercise
The system SHALL display a table of all cognitive sessions for the exercise, with columns: student ID, status, N1-N4 scores, risk level, and a link to the full trace.

#### Scenario: Click to trace
- **WHEN** a docente clicks a session row
- **THEN** the browser SHALL navigate to `/teacher/trace/{sessionId}`
