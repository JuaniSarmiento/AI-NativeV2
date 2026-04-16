## ADDED Requirements

### Requirement: Create reflection endpoint
POST /api/v1/submissions/{activity_submission_id}/reflection — alumno creates reflection.

#### Scenario: Alumno creates reflection
- **WHEN** alumno sends POST with all 5 required fields
- **THEN** reflection is created and returned with 201 status

#### Scenario: Missing fields rejected
- **WHEN** any required field is missing
- **THEN** 422 Unprocessable Entity

### Requirement: Read reflection endpoint
GET /api/v1/submissions/{activity_submission_id}/reflection — read reflection.

#### Scenario: Alumno reads own reflection
- **WHEN** alumno requests their own reflection
- **THEN** the reflection is returned

#### Scenario: Docente reads student reflection
- **WHEN** docente requests a student's reflection from their commission
- **THEN** the reflection is returned

#### Scenario: No reflection exists
- **WHEN** no reflection exists for the submission
- **THEN** 404 Not Found
