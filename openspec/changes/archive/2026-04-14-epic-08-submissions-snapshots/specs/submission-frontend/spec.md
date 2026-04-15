## ADDED Requirements

### Requirement: Auto-snapshot in activity view
The frontend SHALL automatically save a code snapshot every 30 seconds if the code changed since the last snapshot. It SHALL also save a snapshot before each code execution.

#### Scenario: Snapshot sent every 30s
- **WHEN** the student modifies code and 30 seconds pass
- **THEN** a snapshot SHALL be sent to the backend

#### Scenario: No snapshot if code unchanged
- **WHEN** 30 seconds pass but the student hasn't modified code
- **THEN** no snapshot SHALL be sent

### Requirement: Submit activity button
The student activity view SHALL have a "Enviar actividad" button on the last exercise that creates submissions for all exercises. A confirmation dialog SHALL appear before submitting.

#### Scenario: Student confirms and submits
- **WHEN** a student clicks "Enviar actividad" and confirms
- **THEN** the system SHALL send all exercise codes and show a success message

#### Scenario: Student cancels submission
- **WHEN** a student clicks "Enviar actividad" but cancels the confirmation
- **THEN** nothing SHALL happen

### Requirement: Submission history page
The system SHALL provide a way for the student to see their submission history for an activity, showing attempt number, submitted date, and status.

#### Scenario: Student sees past attempts
- **WHEN** a student navigates to submission history
- **THEN** they SHALL see all their attempts with dates
