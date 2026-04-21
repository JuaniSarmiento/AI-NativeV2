## ADDED Requirements

### Requirement: Automatic LLM provider fallback
The system SHALL attempt the secondary LLM provider when the primary provider raises `LLMUnavailableError`. Fallback SHALL be configurable via environment variable `TUTOR_LLM_FALLBACK` (default: false).

#### Scenario: Primary provider fails, fallback enabled
- **WHEN** `TUTOR_LLM_FALLBACK=true` AND the primary LLM provider raises `LLMUnavailableError`
- **THEN** the system SHALL retry the same request with the secondary provider
- **THEN** the system SHALL log a warning indicating fallback activation with both provider names

#### Scenario: Primary provider fails, fallback disabled
- **WHEN** `TUTOR_LLM_FALLBACK=false` AND the primary provider raises `LLMUnavailableError`
- **THEN** the system SHALL propagate the error to the caller without retry

#### Scenario: Both providers fail
- **WHEN** both primary and secondary providers raise `LLMUnavailableError`
- **THEN** the system SHALL raise `LLMUnavailableError` to the caller

#### Scenario: Fallback usage logged in governance
- **WHEN** a fallback activation occurs
- **THEN** the system SHALL record a governance event with `event_type="llm.fallback_activated"` including the primary provider error and the secondary provider used
