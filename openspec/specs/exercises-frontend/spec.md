## ADDED Requirements

### Requirement: Docente exercise management page
The system SHALL provide a page for docente/admin to list, create, edit, and delete exercises within a course. The create/edit form SHALL include fields for title, description, difficulty, topic tags, starter code, and test cases.

#### Scenario: Docente creates an exercise
- **WHEN** a docente fills the form and submits
- **THEN** the exercise SHALL appear in the list without page reload

### Requirement: Alumno exercises page
The system SHALL provide a page at `/exercises` for alumno showing exercises from enrolled courses with filters for difficulty and topic.

#### Scenario: Alumno filters by difficulty
- **WHEN** an alumno selects "easy" difficulty filter
- **THEN** only easy exercises SHALL be displayed

### Requirement: Exercise detail page
The system SHALL provide a detail page at `/exercises/:id` showing the exercise title, description, difficulty, topics, and starter code. For alumno, this triggers the `reads_problem` event.

#### Scenario: Alumno sees exercise detail
- **WHEN** an alumno navigates to exercise detail
- **THEN** the full enunciado, difficulty badge, topics, and starter code SHALL be displayed
