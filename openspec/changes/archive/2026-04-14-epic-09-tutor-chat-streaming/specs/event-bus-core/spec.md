## MODIFIED Requirements

### Requirement: Event payload structure
All events published through the EventBus SHALL follow a consistent payload structure.

#### Scenario: Event has standard fields
- **WHEN** an event is published
- **THEN** it SHALL include at minimum: `event_id` (UUID), `event_type` (string), `timestamp` (ISO 8601 UTC), `source` (producing service/phase), and `data` (domain-specific payload)

#### Scenario: Outbox worker routes events to correct stream
- **WHEN** the outbox worker processes a pending event
- **THEN** it SHALL route the event to the correct Redis Stream based on this mapping:
  - `reads_problem`, `exercise.submitted`, `reflection.submitted` → `events:submissions`
  - `code.executed`, `code.execution.failed`, `code.snapshot.captured` → `events:code`
  - `tutor.session.started`, `tutor.interaction.completed`, `tutor.session.ended` → `events:tutor`
  - `cognitive.classified`, `ctr.entry.created`, `ctr.hash.verified` → `events:cognitive`
  - `governance.flag.raised`, `governance.prompt_updated` → `events:cognitive`
