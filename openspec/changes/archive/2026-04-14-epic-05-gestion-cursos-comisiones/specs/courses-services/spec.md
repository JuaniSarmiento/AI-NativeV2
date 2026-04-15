## ADDED Requirements

### Requirement: CourseService domain logic
The system SHALL provide a CourseService handling: create course (validate name uniqueness), update course, soft delete course, list with pagination.

#### Scenario: Duplicate course name rejected
- **WHEN** a course is created with a name that already exists (active)
- **THEN** the service SHALL raise ConflictError

### Requirement: CommissionService domain logic
The system SHALL provide a CommissionService handling: create commission (validate course exists and is active), update, soft delete.

#### Scenario: Commission on inactive course rejected
- **WHEN** a commission is created for an inactive course
- **THEN** the service SHALL raise ValidationError

### Requirement: EnrollmentService domain logic
The system SHALL provide an EnrollmentService handling: enroll (validate commission active, course active, no duplicate), list student courses. On successful enrollment, it SHALL write an `enrollment.created` event to the event_outbox.

#### Scenario: Enroll writes outbox event
- **WHEN** an enrollment is created successfully
- **THEN** an event with type `enrollment.created` SHALL exist in the event_outbox table

#### Scenario: Enroll in inactive commission rejected
- **WHEN** a student tries to enroll in an inactive commission
- **THEN** the service SHALL raise ValidationError
