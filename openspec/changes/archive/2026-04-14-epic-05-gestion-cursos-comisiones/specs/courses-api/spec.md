## ADDED Requirements

### Requirement: Course CRUD endpoints
The system SHALL expose: `GET /api/v1/courses` (paginated, docente/admin), `POST /api/v1/courses` (docente/admin), `GET /api/v1/courses/{id}` (authenticated), `PUT /api/v1/courses/{id}` (docente/admin), `DELETE /api/v1/courses/{id}` (admin, soft delete).

#### Scenario: List courses with pagination
- **WHEN** `GET /api/v1/courses?page=1&per_page=10` is called by a docente
- **THEN** the response SHALL be a PaginatedResponse with courses and meta

#### Scenario: Create course
- **WHEN** `POST /api/v1/courses` is called by a docente with valid data
- **THEN** the system SHALL return 201 with the created course

#### Scenario: Alumno cannot create course
- **WHEN** an alumno calls `POST /api/v1/courses`
- **THEN** the system SHALL return 403

### Requirement: Commission CRUD endpoints
The system SHALL expose: `GET /api/v1/courses/{id}/commissions` (paginated), `POST /api/v1/courses/{id}/commissions` (docente/admin), `GET /api/v1/commissions/{id}`, `PUT /api/v1/commissions/{id}`, `DELETE /api/v1/commissions/{id}` (admin, soft delete).

#### Scenario: List commissions for a course
- **WHEN** `GET /api/v1/courses/{id}/commissions` is called
- **THEN** the response SHALL return commissions belonging to that course

### Requirement: Enrollment endpoint
The system SHALL expose `POST /api/v1/commissions/{id}/enroll` (alumno) to create an enrollment.

#### Scenario: Alumno enrolls successfully
- **WHEN** an alumno calls enroll on an active commission
- **THEN** the system SHALL create the enrollment and return 201

#### Scenario: Duplicate enrollment rejected
- **WHEN** an alumno tries to enroll in a commission they are already enrolled in
- **THEN** the system SHALL return 409 Conflict

### Requirement: Student courses endpoint
The system SHALL expose `GET /api/v1/student/courses` returning courses the authenticated alumno is enrolled in.

#### Scenario: Student sees enrolled courses
- **WHEN** an alumno calls `GET /api/v1/student/courses`
- **THEN** the response SHALL include only courses where the student has an active enrollment
