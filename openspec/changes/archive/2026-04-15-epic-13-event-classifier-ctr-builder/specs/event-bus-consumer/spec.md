## ADDED Requirements

### Requirement: Redis Streams consumer with consumer group
The system SHALL consume from events:submissions, events:tutor, events:code using consumer group cognitive-group.

#### Scenario: Consumer processes events from all 3 streams
- **WHEN** events are published to any of the 3 streams
- **THEN** the consumer SHALL read, process, and ACK each event

#### Scenario: Consumer runs as asyncio task in app lifecycle
- **WHEN** the FastAPI app starts
- **THEN** the consumer SHALL start as a background task and stop on shutdown

#### Scenario: Consumer handles reconnection
- **WHEN** Redis connection is lost
- **THEN** the consumer SHALL reconnect with backoff and resume processing
