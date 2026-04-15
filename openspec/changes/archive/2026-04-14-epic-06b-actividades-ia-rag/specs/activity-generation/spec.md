## ADDED Requirements

### Requirement: Activity generation service
The system SHALL provide an `ActivityGenerationService` that receives a docente's prompt, searches relevant RAG chunks, constructs an LLM prompt with context, calls the docente's configured LLM, parses the response into an Activity with exercises, and persists them as draft.

#### Scenario: Docente generates activity
- **WHEN** a docente sends "Creame una actividad de funciones con 3 ejercicios de dificultad progresiva"
- **THEN** the system SHALL create an Activity (draft) with 3 exercises with difficulty easy/medium/hard, each with title, description, test_cases, and starter_code derived from the RAG context

#### Scenario: Generation fails gracefully
- **WHEN** the LLM returns invalid JSON or the API key is wrong
- **THEN** the system SHALL return a clear error without crashing

### Requirement: Activity generation endpoint
The system SHALL expose `POST /api/v1/activities/generate` accepting `{ prompt: str, course_id: UUID }` and returning the generated Activity with its exercises.

#### Scenario: Generate returns draft activity
- **WHEN** the endpoint is called with a valid prompt
- **THEN** the response SHALL contain the Activity in draft status with its exercises

### Requirement: Activity CRUD endpoints
The system SHALL expose: `GET /api/v1/activities` (list, docente), `GET /api/v1/activities/{id}` (detail with exercises), `PUT /api/v1/activities/{id}` (edit), `POST /api/v1/activities/{id}/publish` (change status to published, activate exercises), `DELETE /api/v1/activities/{id}` (soft delete).

#### Scenario: Publish activates exercises
- **WHEN** a docente publishes an activity
- **THEN** the activity status SHALL change to published and all its exercises SHALL have is_active=True

### Requirement: Multi-provider LLM adapter
The system SHALL provide an LLM adapter protocol with implementations for OpenAI and Anthropic. The adapter is selected based on the docente's LLMConfig.provider.

#### Scenario: OpenAI adapter calls chat completions
- **WHEN** the docente has provider=openai configured
- **THEN** the system SHALL use the OpenAI chat completions API

#### Scenario: Anthropic adapter calls messages API
- **WHEN** the docente has provider=anthropic configured
- **THEN** the system SHALL use the Anthropic messages API
