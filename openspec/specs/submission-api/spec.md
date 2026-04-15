## ADDED Requirements

### Requirement: Submit activity endpoint
The system SHALL expose `POST /api/v1/student/activities/{id}/submit` accepting `{ exercises: [{ exercise_id, code }] }`. It SHALL create an ActivitySubmission + one Submission per exercise, emit events, and return the activity submission.

#### Scenario: Successful submission
- **WHEN** a student submits an activity with code for all exercises
- **THEN** the system SHALL create submissions and return 201

#### Scenario: Missing exercise code rejected
- **WHEN** a student submits without code for one exercise
- **THEN** the system SHALL return 422 with the missing exercise

#### Scenario: Events emitted
- **WHEN** a submission is created
- **THEN** `exercise.submitted` events SHALL be written to event_outbox for each exercise

### Requirement: Snapshot endpoint
The system SHALL expose `POST /api/v1/student/exercises/{id}/snapshot` accepting `{ code }`. Fire-and-forget, always 201.

#### Scenario: Snapshot saved
- **WHEN** the frontend sends a snapshot
- **THEN** it SHALL be persisted and a `code.snapshot.captured` event written to outbox

### Requirement: Student submissions list
The system SHALL expose `GET /api/v1/student/activities/{id}/submissions` returning the student's activity submissions with exercise submissions.

#### Scenario: Student sees submission history
- **WHEN** a student calls the endpoint
- **THEN** they SHALL see all their attempts with status and submitted_at

### Requirement: Docente submissions view
The system SHALL expose `GET /api/v1/activities/{id}/submissions` (docente/admin) returning all student submissions for that activity.

#### Scenario: Docente sees all student submissions
- **WHEN** a docente calls the endpoint
- **THEN** they SHALL see submissions from all students with code and status
