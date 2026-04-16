## MODIFIED Requirements

### Requirement: Tutor messages REST endpoint
The system SHALL provide `GET /api/v1/tutor/sessions/{exercise_id}/messages` for alumno role, returning the last 50 messages of the authenticated student's session. Additionally, the system SHALL provide `GET /api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages` for docente/admin role to read any student's chat. Both endpoints SHALL return the same `MessagesListResponse` schema.

#### Scenario: Alumno reads own messages
- **WHEN** an alumno calls GET `/api/v1/tutor/sessions/{exercise_id}/messages`
- **THEN** the system SHALL return messages filtered by the authenticated student's ID

#### Scenario: Docente reads student messages
- **WHEN** a docente calls GET `/api/v1/teacher/students/{student_id}/exercises/{exercise_id}/messages`
- **THEN** the system SHALL return messages for the specified student
