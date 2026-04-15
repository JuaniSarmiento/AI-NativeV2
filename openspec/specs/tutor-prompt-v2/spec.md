## Purpose

Defines the v2 socratic system prompt with dynamic context placeholders, anti-solver rules, and seed script behavior for prompt versioning.

## Requirements

### Requirement: System prompt v2 contains dynamic context placeholders
The v2 system prompt SHALL contain placeholders for exercise context, student code, and pedagogical constraints that ContextBuilder fills at runtime.

#### Scenario: Prompt template has all required placeholders
- **WHEN** the v2 prompt template is loaded
- **THEN** it SHALL contain placeholders for: exercise_title, exercise_description, exercise_difficulty, exercise_topics, exercise_language, exercise_rubric, student_code, and constraints section

#### Scenario: Prompt is versioned with SHA-256
- **WHEN** the v2 prompt is seeded via seed.py
- **THEN** it SHALL have a unique sha256_hash computed from its content, name `socratic_tutor_contextual_v2`, and version `v2.0.0`

### Requirement: System prompt v2 includes anti-solver rules
The v2 prompt SHALL embed explicit rules preventing the tutor from providing direct solutions.

#### Scenario: Prompt includes code limit rule
- **WHEN** the prompt is rendered
- **THEN** it SHALL contain an explicit instruction limiting code to maximum 5 lines, partial and contextual only

#### Scenario: Prompt includes socratic method enforcement
- **WHEN** the prompt is rendered
- **THEN** it SHALL contain instructions to always respond with guiding questions, never give complete solutions, and encourage the student to explain their reasoning

### Requirement: Seed script activates v2 and deactivates v1
The seed.py script SHALL activate the v2 prompt and deactivate any previously active prompts.

#### Scenario: Running seed with existing v1 active
- **WHEN** seed_default_prompt runs and v1 is currently active
- **THEN** v1 SHALL be deactivated (is_active=False) and v2 SHALL be activated (is_active=True)

#### Scenario: Running seed when v2 already exists
- **WHEN** seed_default_prompt runs and v2 already exists (same sha256_hash)
- **THEN** no duplicate SHALL be created
