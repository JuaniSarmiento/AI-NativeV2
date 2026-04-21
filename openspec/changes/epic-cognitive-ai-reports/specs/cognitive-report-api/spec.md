## ADDED Requirements

### Requirement: POST endpoint to generate a report
The system SHALL expose `POST /api/v1/reports/generate` accepting `student_id`, `activity_id`, and `commission_id`. Access requires role docente or admin.

#### Scenario: Successful report generation
- **WHEN** a docente POSTs with valid student_id, activity_id, commission_id and the student has closed sessions
- **THEN** the system returns 200 with the generated report (id, narrative_md, structured_analysis, generated_at)

#### Scenario: Cached report returned
- **WHEN** a docente requests a report and a cached report exists with matching data_hash
- **THEN** the system returns the cached report without calling the LLM

#### Scenario: No closed sessions for student+activity
- **WHEN** a docente requests a report but the student has no closed sessions for that activity
- **THEN** the system returns 400 with error message "No hay sesiones cerradas para analizar"

### Requirement: GET endpoint to retrieve existing report
The system SHALL expose `GET /api/v1/reports/{report_id}` returning a previously generated report. Access requires role docente or admin.

#### Scenario: Report exists
- **WHEN** a docente GETs a valid report_id
- **THEN** the system returns 200 with the full report data

#### Scenario: Report not found
- **WHEN** a docente GETs a non-existent report_id
- **THEN** the system returns 404

### Requirement: GET endpoint to list reports for student+activity
The system SHALL expose `GET /api/v1/reports?student_id=X&activity_id=Y&commission_id=Z` returning the most recent report for that combination.

#### Scenario: Report exists for combination
- **WHEN** a docente queries with valid filters and a report exists
- **THEN** the system returns 200 with the latest report

#### Scenario: No report exists
- **WHEN** a docente queries but no report has been generated yet
- **THEN** the system returns 200 with null data
