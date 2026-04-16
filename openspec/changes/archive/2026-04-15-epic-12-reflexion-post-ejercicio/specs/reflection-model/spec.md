## ADDED Requirements

### Requirement: Reflection model in operational schema
The system SHALL have a Reflection model associated with ActivitySubmission, with guided metacognitive fields.

#### Scenario: Model has all required fields
- **WHEN** the Reflection model is defined
- **THEN** it SHALL have: id UUID PK, activity_submission_id FK UNIQUE, student_id FK, difficulty_perception INT CHECK 1-5, strategy_description TEXT, ai_usage_evaluation TEXT, what_would_change TEXT, confidence_level INT CHECK 1-5, created_at TIMESTAMPTZ

#### Scenario: One reflection per submission enforced
- **WHEN** a student tries to create a second reflection for the same activity_submission
- **THEN** the database UNIQUE constraint SHALL prevent the duplicate
