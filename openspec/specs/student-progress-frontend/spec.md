## ADDED Requirements

### Requirement: Student progress page
The system SHALL provide a student progress page at route `/student/progress`. The page SHALL display the authenticated student's cognitive evolution over time using aggregated scores. Design: minimalist UI with the project's design system tokens. The page SHALL NOT expose information that enables gaming (no dependency scores, no risk levels, no per-session breakdowns).

#### Scenario: Student with progress data
- **WHEN** an alumno navigates to their progress page
- **THEN** the page SHALL display: evolution chart (line chart with N1-N4 over time), current aggregated score cards, and a brief text explanation of what each dimension means

#### Scenario: Student with no sessions
- **WHEN** an alumno has no closed cognitive sessions
- **THEN** the page SHALL display an empty state message: "Aún no tenés datos de progreso. Completá ejercicios para ver tu evolución."

### Requirement: Evolution chart
The system SHALL render a line chart (Recharts) showing N1-N4 score trends over the student's sessions. X-axis: session date. Y-axis: score 0-100. Each N-level is a separate line with distinct color.

#### Scenario: Multiple sessions
- **WHEN** a student has 5+ closed sessions
- **THEN** the chart SHALL show score evolution with one data point per session, sorted chronologically

### Requirement: Aggregated score cards
The system SHALL display 4 score cards (one per N-level) showing the student's latest aggregated score. Cards SHALL use the design system's Card pattern and display a brief Spanish label for each dimension.

#### Scenario: Score card display
- **WHEN** progress data loads
- **THEN** each card SHALL show: dimension name in Spanish (e.g., "Comprensión"), current score (0-100), and a subtle trend indicator (up/down/stable compared to previous session)

### Requirement: Anti-gaming data restriction
The student progress frontend SHALL only consume data from `GET /api/v1/student/me/progress`. It SHALL NOT display: dependency_score, risk_level, help_seeking_ratio, qe sub-scores, or individual session metric breakdowns.

#### Scenario: Response data contract
- **WHEN** the frontend renders progress
- **THEN** it SHALL only use fields: n1_score, n2_score, n3_score, n4_score, qe_score (aggregate), and session timestamps
