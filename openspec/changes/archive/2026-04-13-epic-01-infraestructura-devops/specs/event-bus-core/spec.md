## ADDED Requirements

### Requirement: Four Redis Streams for cross-phase events
The system SHALL create 4 Redis Streams: `events:submissions`, `events:tutor`, `events:code`, `events:cognitive`. Each stream SHALL have at least one consumer group initialized.

#### Scenario: Streams exist on startup
- **WHEN** the application starts
- **THEN** all 4 Redis Streams SHALL exist with their consumer groups created (idempotently, without error if they already exist)

#### Scenario: Consumer groups are named by phase
- **WHEN** a consumer group is created for a stream
- **THEN** it SHALL follow the naming convention `group:<phase>` (e.g., `group:cognitive` for the cognitive phase consumer)

### Requirement: EventBus class with publish and subscribe
An `EventBus` class in `app/core/event_bus.py` SHALL provide `publish(stream, event_type, payload)` and `subscribe(stream, group, consumer, callback)` methods.

#### Scenario: Publish adds message to stream
- **WHEN** a service calls `event_bus.publish("events:submissions", "submission.created", {"submission_id": "..."})`
- **THEN** a new entry SHALL be added to the `events:submissions` Redis Stream with the event type and JSON payload

#### Scenario: Subscribe receives messages
- **WHEN** a consumer subscribes to a stream via `event_bus.subscribe("events:submissions", "group:cognitive", "worker-1", callback)`
- **THEN** the callback SHALL be invoked for each new message in the stream, receiving the event type and parsed payload

#### Scenario: Subscribe handles connection errors
- **WHEN** the Redis connection is lost during subscription
- **THEN** the EventBus SHALL attempt reconnection with exponential backoff and log the error

#### Scenario: Messages are acknowledged after processing
- **WHEN** a callback completes successfully
- **THEN** the message SHALL be acknowledged (XACK) so it is not redelivered to the same consumer group

### Requirement: Event outbox table for transactional reliability
A table `event_outbox` in the `operational` schema SHALL store events within the same database transaction as the domain operation.

#### Scenario: Outbox record is created
- **WHEN** a domain service inserts an event into the outbox
- **THEN** the record SHALL contain `id` (UUID), `event_type` (VARCHAR 100), `payload` (JSONB), `status` (pending), `created_at` (TIMESTAMPTZ), and `retry_count` (0)

#### Scenario: Outbox worker publishes pending events
- **WHEN** the outbox worker runs
- **THEN** it SHALL read all records with `status = 'pending'`, publish them to the corresponding Redis Stream, and update `status` to `'processed'` with `processed_at` timestamp

#### Scenario: Failed publish is retried
- **WHEN** publishing an outbox event to Redis fails
- **THEN** the worker SHALL increment `retry_count` and set `status` to `'failed'` if `retry_count` exceeds 5

### Requirement: Event payload structure
All events published through the EventBus SHALL follow a consistent payload structure.

#### Scenario: Event has standard fields
- **WHEN** an event is published
- **THEN** it SHALL include at minimum: `event_id` (UUID), `event_type` (string), `timestamp` (ISO 8601 UTC), `source` (producing service/phase), and `data` (domain-specific payload)
