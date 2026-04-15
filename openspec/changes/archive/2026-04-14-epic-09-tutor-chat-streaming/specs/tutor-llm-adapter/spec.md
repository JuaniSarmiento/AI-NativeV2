## ADDED Requirements

### Requirement: LLMAdapter interface
The system SHALL define an `LLMAdapter` abstract interface with a `stream_response(messages, system_prompt, config)` method that yields tokens.

#### Scenario: Adapter yields tokens from LLM response
- **WHEN** `stream_response` is called with a message history and system prompt
- **THEN** it SHALL yield string tokens as they arrive from the LLM provider

#### Scenario: Adapter raises on API error
- **WHEN** the LLM provider returns an error (rate limit, server error, invalid request)
- **THEN** the adapter SHALL raise a domain exception (`LLMError`, `LLMRateLimitError`, `LLMUnavailableError`)

### Requirement: AnthropicAdapter implementation
The system SHALL implement `AnthropicAdapter` using the `anthropic` Python SDK with streaming.

#### Scenario: Streaming with Anthropic SDK
- **WHEN** `stream_response` is called on `AnthropicAdapter`
- **THEN** it SHALL use `client.messages.stream()` with the configured model and `max_tokens`

#### Scenario: Token counting after response
- **WHEN** a streaming response completes
- **THEN** the adapter SHALL return the total `input_tokens` and `output_tokens` from the response usage metadata

#### Scenario: Model is configurable
- **WHEN** the adapter is initialized
- **THEN** it SHALL read the model name from config (default: `claude-haiku-4-5-20251001` in dev, `claude-sonnet-4-5-20241022` in prod)

### Requirement: Timeout and max_tokens configuration
The system SHALL enforce configurable timeout and max_tokens limits on LLM calls.

#### Scenario: Response exceeds max_tokens
- **WHEN** the LLM response reaches `max_tokens` (default 1024)
- **THEN** the response SHALL be truncated at the token limit

#### Scenario: Request times out
- **WHEN** the LLM does not start responding within 30 seconds
- **THEN** the adapter SHALL raise `LLMUnavailableError`
