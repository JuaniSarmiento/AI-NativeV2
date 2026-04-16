## MODIFIED Requirements

### Requirement: Sessions list endpoint for navigation
The system SHALL provide `GET /api/v1/cognitive/sessions` with query params `commission_id` (required), `student_id` (optional), `exercise_id` (optional), `status` (optional), `page` (default 1), `per_page` (default 20, max 100). Returns paginated list of cognitive sessions with fields: id, student_id, exercise_id, commission_id, started_at, closed_at, status. Requires role docente or admin. Response SHALL follow the standard envelope format.

#### Scenario: List sessions for a commission
- **WHEN** a docente calls GET `/api/v1/cognitive/sessions?commission_id={id}`
- **THEN** the system SHALL return all cognitive sessions for that commission ordered by started_at DESC with pagination meta

#### Scenario: Filter by student
- **WHEN** a docente adds `student_id={id}` query param
- **THEN** only sessions for that student SHALL be returned

#### Scenario: Unauthorized access
- **WHEN** an alumno calls this endpoint
- **THEN** the system SHALL return 403 Forbidden
