## ADDED Requirements

### Requirement: Mini-bars N1-N4 in commission student table
The student table SHALL display 4 mini horizontal bars (one per N-dimension) in each student row, color-coded: green (>=70), yellow (40-69), red (<40), gray (null).

#### Scenario: Student with mixed scores
- **WHEN** student has N1=75, N2=35, N3=80, N4=null
- **THEN** table shows green bar for N1, red bar for N2, green bar for N3, gray bar with "Sin interaccion" for N4

#### Scenario: All students visible at once
- **WHEN** docente views the commission table
- **THEN** the mini-bars provide a visual cognitive profile for each student without needing to expand/click

### Requirement: Appropriation type column
The student table SHALL display an "Apropiacion" column showing the dominant appropriation type derived from prompt_type_distribution: "Delegacion" (>60% generative), "Reflexiva" (exploratory dominant with verification), "Superficial" (mixed without clear pattern).

#### Scenario: Student with mostly generative prompts
- **WHEN** student's prompt_type_distribution has generative > 60%
- **THEN** column shows "Delegacion" with red-tinted badge

#### Scenario: Student with exploratory + verifier mix
- **WHEN** exploratory > 40% AND verifier > 10%
- **THEN** column shows "Reflexiva" with green-tinted badge

#### Scenario: Student without tutor interaction
- **WHEN** N4 is null (no tutor usage)
- **THEN** column shows "Autonomo" with neutral badge

### Requirement: Sort by individual N dimensions
The student table SHALL allow sorting by N1, N2, N3, N4 individually (ascending/descending).

#### Scenario: Docente sorts by N2 ascending
- **WHEN** docente clicks on N2 column header
- **THEN** students are sorted by latest_n2 ascending, showing weakest strategists first

### Requirement: Score breakdown with reasons in student detail
When a student is expanded/selected, each N-score SHALL show a breakdown of contributing conditions with checkmark (met) or cross (unmet) indicators.

#### Scenario: N1=35 breakdown display
- **WHEN** docente views student detail with N1=35
- **THEN** display shows: "✓ Leyo el enunciado >15 seg (+15)", "✗ No releyo el enunciado (0)", "✓ Pregunto al tutor sobre comprension (+20)", "✗ No leyo >45 seg (0)"

#### Scenario: All conditions met
- **WHEN** all conditions for N2 are satisfied
- **THEN** all items show checkmarks and score = 100 or near-maximum

### Requirement: Coherence traffic lights in student detail
The student detail view SHALL display 3 coherence indicators as color-coded traffic lights: temporal_coherence, code_discourse, inter_iteration.

#### Scenario: Mixed coherence scores
- **WHEN** temporal=85, code_discourse=52, inter_iteration=28
- **THEN** display shows green circle (85), yellow circle (52), red circle (28) with labels and one-line explanations

### Requirement: N4=null displays "Sin interaccion" explicitly
When N4 score is null, the dashboard SHALL display "Sin interaccion" text instead of "-" or "0", communicating that the absence of score is due to no tutor usage, not poor performance.

#### Scenario: Autonomous student in table
- **WHEN** student's latest_n4 is null
- **THEN** N4 mini-bar shows gray with text "Sin interaccion"

### Requirement: Evolution chart across sessions
A new visualization SHALL show N1-N4 scores as 4 lines across sessions (X-axis = session chronological order, Y-axis = 0-100).

#### Scenario: Student with 5 sessions
- **WHEN** docente views student with 5 closed sessions
- **THEN** line chart shows 4 colored lines (one per N) with 5 data points each, showing trends

#### Scenario: Student with 1 session
- **WHEN** student has only 1 session
- **THEN** chart shows 4 dots (single point per line) with no trend line

### Requirement: Swim lanes timeline in trace view
The trace detail view SHALL display a swim lanes visualization with 4 horizontal lanes (N1, N2, N3, N4) and events plotted as colored dots on their corresponding lane at their temporal position.

#### Scenario: Session with mixed events
- **WHEN** session has events across all 4 levels over 20 minutes
- **THEN** SVG shows 4 labeled lanes with dots positioned by time, showing the cognitive flow pattern

#### Scenario: Hover on event dot
- **WHEN** docente hovers over a dot in the swim lanes
- **THEN** tooltip shows event_type, timestamp, and brief payload summary

#### Scenario: Session dominated by N4
- **WHEN** most events are N4 (tutor questions)
- **THEN** N4 lane is densely populated, visually communicating dependency pattern

### Requirement: New endpoint for student evolution data
The API SHALL provide `GET /api/v1/cognitive/students/{student_id}/evolution?commission_id=X` returning N1-N4 scores per session ordered chronologically.

#### Scenario: Request evolution for student with 5 sessions
- **WHEN** GET request for student evolution
- **THEN** response contains array of `{session_id, exercise_title, started_at, n1, n2, n3, n4, qe}` ordered by started_at ASC

#### Scenario: Student with no closed sessions
- **WHEN** student has only open sessions (no metrics computed)
- **THEN** response returns empty array with status 200
