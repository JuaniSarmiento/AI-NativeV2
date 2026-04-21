## ADDED Requirements

### Requirement: Report view component
The system SHALL display the AI-generated report as rendered Markdown within the teacher dashboard, showing all 5 sections with proper formatting.

#### Scenario: Report loaded successfully
- **WHEN** a docente clicks "Ver Informe" for a student in an activity
- **THEN** the system fetches or generates the report and displays it as formatted Markdown with section headers

#### Scenario: Report is loading
- **WHEN** the report is being generated (LLM call in progress)
- **THEN** the UI shows a loading spinner with text "Generando informe..."

#### Scenario: Generation fails
- **WHEN** report generation fails (invalid API key, no data, etc.)
- **THEN** the UI shows an error message with the specific reason

### Requirement: Report accessible from student list in activity view
The system SHALL add a "Ver Informe" action button next to each student who has at least one closed session in the selected activity.

#### Scenario: Student has sessions — button visible
- **WHEN** viewing the activity's student list and a student has closed sessions
- **THEN** a "Ver Informe" button is visible next to that student

#### Scenario: Student has no sessions — button disabled
- **WHEN** viewing the activity's student list and a student has no closed sessions
- **THEN** the button is either hidden or disabled with tooltip "Sin sesiones cerradas"
