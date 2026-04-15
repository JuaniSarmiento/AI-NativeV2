## ADDED Requirements

### Requirement: ContextBuilder composes full system prompt with exercise context
The ContextBuilder service SHALL receive exercise_id and student_id and compose a complete system prompt by combining: the active TutorSystemPrompt template, exercise metadata (title, description, difficulty, topic_tags, language, rubric), and the student's current code (latest CodeSnapshot or starter_code as fallback).

#### Scenario: Exercise with rubric and student code
- **WHEN** ContextBuilder is called with a valid exercise_id that has a rubric and the student has at least one CodeSnapshot
- **THEN** the composed prompt SHALL include the exercise title, description, rubric, difficulty, topic_tags, language, and the student's latest code snapshot

#### Scenario: Exercise without rubric
- **WHEN** ContextBuilder is called with an exercise that has rubric=NULL
- **THEN** the composed prompt SHALL include all exercise metadata except rubric, and the rubric section SHALL be omitted (not empty placeholder)

#### Scenario: Student has no code snapshots
- **WHEN** ContextBuilder is called and the student has no CodeSnapshot for the exercise
- **THEN** the composed prompt SHALL use the exercise's starter_code as the student's current code

#### Scenario: Student has no snapshots and exercise has empty starter_code
- **WHEN** ContextBuilder is called, no CodeSnapshot exists, and starter_code is empty
- **THEN** the composed prompt SHALL indicate "El alumno aun no ha escrito codigo"

### Requirement: ContextBuilder truncates oversized context
The ContextBuilder SHALL enforce size limits on context components to prevent prompt overflow.

#### Scenario: Student code exceeds 2000 characters
- **WHEN** the latest CodeSnapshot code exceeds 2000 characters
- **THEN** the ContextBuilder SHALL truncate to the last 2000 characters and prepend "[...codigo truncado...]"

#### Scenario: Chat history is limited
- **WHEN** ContextBuilder prepares context and there are more than 10 messages in the session
- **THEN** only the last 10 messages SHALL be included in the context window

### Requirement: ContextBuilder includes activity context when exercise belongs to an activity
The ContextBuilder SHALL include the parent Activity's title and description when the exercise has a non-null activity_id.

#### Scenario: Exercise belongs to an activity
- **WHEN** the exercise has activity_id set and the Activity exists
- **THEN** the composed prompt SHALL include the activity title and description as additional context

#### Scenario: Exercise is standalone (no activity)
- **WHEN** the exercise has activity_id=NULL
- **THEN** the composed prompt SHALL not include any activity context section
