## ADDED Requirements

### Requirement: LLM settings page
The system SHALL provide a settings section at `/settings` where the docente can configure their LLM provider (openai/anthropic), API key, and model name.

#### Scenario: Docente saves API key
- **WHEN** a docente enters their API key and saves
- **THEN** a success message SHALL appear and the key SHALL be stored encrypted

#### Scenario: Settings shows current provider without key
- **WHEN** a docente visits settings with an existing config
- **THEN** the provider and model SHALL be shown but the API key field SHALL be empty (masked)

### Requirement: Activity generation chat page
The system SHALL provide a page at `/activities/new` with a chat-like interface where the docente types what kind of activity they want. After submitting, the system generates the activity and displays the result.

#### Scenario: Docente submits generation prompt
- **WHEN** a docente types "3 ejercicios sobre listas de dificultad creciente" and clicks generate
- **THEN** a loading state SHALL appear, followed by the generated activity with its exercises displayed for review

#### Scenario: No LLM configured shows warning
- **WHEN** a docente without LLM config visits the generation page
- **THEN** a warning SHALL direct them to configure their API key in settings

### Requirement: Activity review and publish page
The system SHALL provide a page at `/activities/{id}` showing the draft activity with all generated exercises. The docente can edit any exercise, delete exercises, and publish the activity.

#### Scenario: Docente edits generated exercise
- **WHEN** a docente modifies the title or description of a generated exercise
- **THEN** the change SHALL persist without regenerating the whole activity

#### Scenario: Docente publishes activity
- **WHEN** a docente clicks publish
- **THEN** the activity and its exercises SHALL become visible to enrolled students
