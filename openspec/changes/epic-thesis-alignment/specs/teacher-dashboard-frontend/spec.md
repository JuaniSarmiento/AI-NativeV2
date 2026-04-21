## ADDED Requirements

### Requirement: Coherence semaphore indicators
The teacher dashboard SHALL display three traffic-light indicators per student for temporal coherence, code-discourse coherence, and inter-iteration coherence.

#### Scenario: Student with high coherence scores
- **WHEN** a student has coherence scores above 70
- **THEN** the corresponding semaphore SHALL display as green
- **THEN** hovering over the semaphore SHALL show a tooltip with the exact numeric score

#### Scenario: Student with medium coherence scores
- **WHEN** a student has coherence scores between 40 and 70
- **THEN** the corresponding semaphore SHALL display as yellow

#### Scenario: Student with low coherence scores
- **WHEN** a student has coherence scores below 40
- **THEN** the corresponding semaphore SHALL display as red

#### Scenario: Student with null coherence score
- **WHEN** a student has no coherence data (null score)
- **THEN** the semaphore SHALL display as gray
- **THEN** the tooltip SHALL show "Sin datos"

### Requirement: Score breakdown detail panel
The teacher dashboard SHALL provide an expandable detail panel per student showing per-N event contributions with check/cross indicators.

#### Scenario: Expand student score breakdown
- **WHEN** a teacher clicks on a student row to expand details
- **THEN** the system SHALL display a breakdown for each N level (N1-N4)
- **THEN** each condition that contributed to the score SHALL show a check icon
- **THEN** each condition that was NOT met SHALL show a cross icon with a description

#### Scenario: Student with no score breakdown data
- **WHEN** a student's `latest_score_breakdown` is null
- **THEN** the detail panel SHALL display "Sin desglose disponible"
