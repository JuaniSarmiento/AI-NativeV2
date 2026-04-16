## ADDED Requirements

### Requirement: ReflectionService creates reflections with validation
The service SHALL validate ownership, submission existence, and uniqueness before creating a reflection.

#### Scenario: Valid reflection created
- **WHEN** an alumno submits a reflection for their own activity_submission
- **THEN** the reflection SHALL be persisted and a reflection.submitted event emitted

#### Scenario: Duplicate reflection rejected
- **WHEN** a reflection already exists for the activity_submission
- **THEN** the service SHALL raise ConflictError

#### Scenario: Wrong student rejected
- **WHEN** a student tries to create a reflection for another student's submission
- **THEN** the service SHALL raise AuthorizationError

### Requirement: ReflectionService emits reflection.submitted event
The service SHALL emit an outbox event for downstream cognitive processing.

#### Scenario: Event emitted on create
- **WHEN** a reflection is successfully created
- **THEN** an EventOutbox record SHALL be created with event_type="reflection.submitted" containing student_id, exercise_id, submission_id, difficulty_perception, confidence_level
