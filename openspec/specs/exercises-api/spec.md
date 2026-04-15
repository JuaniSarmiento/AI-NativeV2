## ADDED Requirements

### Requirement: Exercise CRUD endpoints
The system SHALL expose: `POST /api/v1/courses/{id}/exercises` (docente/admin), `GET /api/v1/courses/{id}/exercises` (authenticated, paginated with filters), `GET /api/v1/exercises/{id}` (authenticated), `PUT /api/v1/exercises/{id}` (docente/admin), `DELETE /api/v1/exercises/{id}` (admin, soft delete).

#### Scenario: Docente creates exercise with test cases
- **WHEN** a docente calls POST with valid exercise data including test_cases
- **THEN** the system SHALL return 201 with the created exercise

#### Scenario: List exercises with filters
- **WHEN** `GET /api/v1/courses/{id}/exercises?difficulty=easy&topic=variables` is called
- **THEN** the response SHALL return only exercises matching both filters

#### Scenario: Alumno cannot create exercise
- **WHEN** an alumno calls POST to create an exercise
- **THEN** the system SHALL return 403

### Requirement: Student exercises endpoint
The system SHALL expose `GET /api/v1/student/exercises` returning exercises from courses the student is enrolled in, with optional filters for difficulty and topic.

#### Scenario: Student sees only enrolled exercises
- **WHEN** an alumno calls student/exercises
- **THEN** the response SHALL include only exercises from courses where the student has an active enrollment

### Requirement: reads_problem event emission
When an authenticated alumno accesses `GET /api/v1/exercises/{id}`, the system SHALL write a `reads_problem` event to the event_outbox with payload `{ student_id, exercise_id, course_id, timestamp }`.

#### Scenario: Event written on exercise detail access
- **WHEN** an alumno accesses exercise detail
- **THEN** an event_outbox row with event_type `reads_problem` SHALL exist

#### Scenario: Docente access does not emit event
- **WHEN** a docente accesses exercise detail
- **THEN** no `reads_problem` event SHALL be written
