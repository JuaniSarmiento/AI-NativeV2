## MODIFIED Requirements

### Requirement: FallbackLLMAdapter wrapper
The LLM adapter layer SHALL support a `FallbackLLMAdapter` that wraps a primary and secondary adapter, retrying with the secondary on `LLMUnavailableError`.

#### Scenario: Primary succeeds
- **WHEN** the primary adapter responds successfully
- **THEN** the FallbackLLMAdapter SHALL return the primary's response
- **THEN** the secondary adapter SHALL NOT be called

#### Scenario: Primary fails, secondary succeeds
- **WHEN** the primary adapter raises `LLMUnavailableError`
- **THEN** the FallbackLLMAdapter SHALL call the secondary adapter
- **THEN** the FallbackLLMAdapter SHALL return the secondary's response
- **THEN** a warning SHALL be logged with the primary's error and secondary's provider name

#### Scenario: Fallback disabled
- **WHEN** `TUTOR_LLM_FALLBACK` is false or unset
- **THEN** `_create_llm_adapter()` SHALL return the primary adapter directly without wrapping
