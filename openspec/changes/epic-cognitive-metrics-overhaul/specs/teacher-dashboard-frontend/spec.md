## MODIFIED Requirements

### Requirement: Student table columns and layout
The student table SHALL display columns: Alumno, Sesiones, N1-N4 (as mini-bars), Apropiacion, Qe, Riesgo, Accion. The table SHALL support sorting by any N dimension.

#### Scenario: Table renders with new columns
- **WHEN** dashboard loads with student data
- **THEN** table shows mini-bars for N1-N4, appropriation badge, and all existing columns

#### Scenario: Sort by N2 descending
- **WHEN** docente clicks N2 header twice
- **THEN** students sorted by latest_n2 descending

### Requirement: Student detail card shows cognitive profile
When a student is selected/expanded, the detail card SHALL show: score breakdown with reasons (checkmarks/crosses), coherence traffic lights, and a link to evolution view.

#### Scenario: Expanded student with breakdown
- **WHEN** docente expands student row
- **THEN** each N-score shows breakdown items with ✓/✗ indicators and point values

#### Scenario: Coherence traffic lights displayed
- **WHEN** student has coherence scores
- **THEN** 3 colored circles (green/yellow/red) with labels: "Temporal", "Codigo-Discurso", "Inter-iteracion"

## ADDED Requirements

### Requirement: SwimLanesTimeline component
A new SVG component SHALL render 4 horizontal lanes (N1, N2, N3, N4) with event dots positioned by time. Dots are colored by level. Hovering shows a tooltip with event details.

#### Scenario: Rendering events
- **WHEN** timeline data contains 20 events across 15 minutes
- **THEN** SVG renders 4 labeled lanes with dots at proportional X positions

#### Scenario: Hover interaction
- **WHEN** docente hovers over a dot
- **THEN** tooltip shows: event_type label, timestamp, n4_level label

#### Scenario: Empty lane
- **WHEN** no N2 events exist
- **THEN** N2 lane is visible but empty (label still shown)

### Requirement: EvolutionChart component
A line chart component SHALL display 4 colored lines (one per N) across sessions on the X-axis (0-100 on Y-axis).

#### Scenario: 5 sessions displayed
- **WHEN** evolution data has 5 entries
- **THEN** chart shows 4 lines with 5 data points each, X-axis labeled with exercise titles or dates

#### Scenario: Null N4 in some sessions
- **WHEN** N4 is null for sessions 1-3 but present for sessions 4-5
- **THEN** N4 line starts at session 4 (gap for earlier sessions)

### Requirement: ScoreBreakdown component
A component SHALL render a list of conditions for a given N-score, each showing met/unmet status, condition description, and point contribution.

#### Scenario: N1 with 3 conditions
- **WHEN** breakdown has 3 entries
- **THEN** renders: "✓ Leyo >15 seg (+15)", "✗ No releyo (0)", "✓ Pregunta N1 al tutor (+20)"

### Requirement: CoherenceTrafficLight component
A component SHALL render 3 horizontal indicators with colored circles and labels.

#### Scenario: All three scores present
- **WHEN** temporal=85, code_discourse=52, inter_iteration=28
- **THEN** green circle + "Temporal: 85", yellow circle + "Codigo-discurso: 52", red circle + "Inter-iteracion: 28"

### Requirement: N4 null display as "Sin interaccion"
All places where N4 is displayed SHALL show "Sin interaccion" text with gray styling when the value is null, instead of "-" or "0".

#### Scenario: Mini-bar for null N4
- **WHEN** latest_n4 is null
- **THEN** mini-bar slot shows gray background with small "Sin interaccion" text

#### Scenario: Detail card for null N4
- **WHEN** N4 score is null in expanded view
- **THEN** card shows "Sin interaccion — El alumno resolvio sin usar el tutor" instead of score
