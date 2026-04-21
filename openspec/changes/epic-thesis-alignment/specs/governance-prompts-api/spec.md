## MODIFIED Requirements

### Requirement: Semantic versioning fields on TutorSystemPrompt
The `TutorSystemPrompt` model SHALL include `change_type` and `change_justification` fields to enforce semantic versioning per the thesis governance requirements.

#### Scenario: Create prompt with major change
- **WHEN** a new prompt is created with `change_type="major"` and `version="3.0.0"`
- **THEN** the system SHALL validate that the major version number incremented from the previous active prompt
- **THEN** the system SHALL require a non-empty `change_justification`

#### Scenario: Create prompt with minor change
- **WHEN** a new prompt is created with `change_type="minor"` and `version="2.1.0"`
- **THEN** the system SHALL validate that the minor version incremented and major stayed the same

#### Scenario: Create prompt with patch change
- **WHEN** a new prompt is created with `change_type="patch"` and `version="2.0.1"`
- **THEN** the system SHALL validate that the patch version incremented and major.minor stayed the same

#### Scenario: Version mismatch with change_type
- **WHEN** a new prompt is created with `change_type="patch"` but the major version changed
- **THEN** the system SHALL reject the request with a validation error explaining the mismatch

#### Scenario: Legacy prompts without change_type
- **WHEN** existing prompts have `change_type=NULL`
- **THEN** the system SHALL continue to function normally — `change_type` is required only for new prompt creation
