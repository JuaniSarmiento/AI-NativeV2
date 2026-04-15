## ADDED Requirements

### Requirement: Docente course management page
The system SHALL provide a page at `/courses` for docente/admin to list, create, edit, and soft-delete courses. The page SHALL use Card (double-bezel) for forms and table with border separators for the list.

#### Scenario: Docente creates a course
- **WHEN** a docente fills the create form and submits
- **THEN** the new course SHALL appear in the list without page reload

#### Scenario: Docente edits a course
- **WHEN** a docente clicks edit on a course, modifies data, and saves
- **THEN** the list SHALL reflect the updated data

### Requirement: Docente commission management
The system SHALL provide commission management within the course detail. A docente can list, create, edit, and delete commissions for a specific course.

#### Scenario: Docente creates a commission
- **WHEN** a docente navigates to a course and creates a commission
- **THEN** the commission SHALL appear in the course's commission list

### Requirement: Alumno courses page
The system SHALL provide a page at `/courses` for alumno showing available courses with enrollment status. The alumno can enroll in a commission via a button.

#### Scenario: Alumno enrolls via UI
- **WHEN** an alumno clicks "Inscribirme" on a commission
- **THEN** the UI SHALL reflect the enrollment immediately and disable the button

### Requirement: MSW handlers for courses
The system SHALL provide MSW handlers for all course/commission/enrollment endpoints returning realistic mock data.

#### Scenario: MSW returns paginated courses
- **WHEN** MSW is active and courses list is requested
- **THEN** the handler SHALL return a PaginatedResponse with mock courses
