## ADDED Requirements

### Requirement: Teacher tutor messages endpoint
The system SHALL provide `GET /api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages` returning the tutor chat history for any student's exercise session. Requires role docente or admin. Returns the same MessagesListResponse format as the alumno endpoint.

#### Scenario: Docente reads student chat
- **WHEN** a docente calls GET with a valid student_id and exercise_id
- **THEN** the system SHALL return the last 50 messages for that student's exercise session

#### Scenario: No messages
- **WHEN** the student has no tutor interactions for that exercise
- **THEN** the system SHALL return an empty data array

#### Scenario: Alumno denied
- **WHEN** an alumno calls this endpoint
- **THEN** the system SHALL return 403 Forbidden
