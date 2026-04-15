## ADDED Requirements

### Requirement: LLM configuration per docente
The system SHALL have an `LLMConfig` model with fields: id (UUID PK), user_id (FK users, UNIQUE), provider (ENUM: openai/anthropic), api_key_encrypted (TEXT), model_name (VARCHAR), created_at, updated_at. The API key SHALL be encrypted with Fernet before storage.

#### Scenario: Docente saves API key
- **WHEN** a docente saves their OpenAI API key
- **THEN** the key SHALL be encrypted and stored, never returned in plaintext

#### Scenario: Docente updates provider
- **WHEN** a docente changes from openai to anthropic with a new key
- **THEN** the old key SHALL be replaced with the new encrypted key

### Requirement: LLM config endpoints
The system SHALL expose `GET /api/v1/settings/llm` (returns provider and model_name, not the key), `PUT /api/v1/settings/llm` (saves/updates provider, api_key, model_name).

#### Scenario: GET does not expose key
- **WHEN** a docente calls GET settings/llm
- **THEN** the response SHALL contain provider and model_name but NOT the api_key
