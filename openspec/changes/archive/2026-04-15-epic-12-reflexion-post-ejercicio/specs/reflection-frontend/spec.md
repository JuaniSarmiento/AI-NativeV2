## ADDED Requirements

### Requirement: Reflection form appears after submission
The frontend SHALL show a guided reflection form after a student submits an activity.

#### Scenario: Student submits activity and sees reflection form
- **WHEN** the student clicks submit and the activity is successfully submitted
- **THEN** the reflection form SHALL appear with 5 guided fields instead of immediate redirect

#### Scenario: Student can skip reflection
- **WHEN** the student does not want to fill the reflection
- **THEN** a "Saltar reflexion" link SHALL allow navigating away

### Requirement: Read-only reflection view
The frontend SHALL show a read-only view when a reflection already exists.

#### Scenario: Student revisits submitted activity
- **WHEN** the student opens an activity they already submitted with reflection
- **THEN** the reflection SHALL be shown in read-only format

### Requirement: Docente sees student reflections
The docente SHALL be able to view student reflections from their commission.

#### Scenario: Docente views student submission with reflection
- **WHEN** docente opens a student's submission detail
- **THEN** the reflection (if exists) SHALL be shown read-only
