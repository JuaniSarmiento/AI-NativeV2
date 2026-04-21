## ADDED Requirements

### Requirement: Detect substantial code changes in editor
The frontend SHALL monitor the code editor content and detect substantial changes defined as: more than 10 lines added/removed since last snapshot, OR more than 3 minutes elapsed since last snapshot.

#### Scenario: Student writes more than 10 lines
- **WHEN** the student has written or deleted more than 10 lines since the last snapshot
- **THEN** the frontend SHALL emit a `code.snapshot.auto` event to the backend
- **THEN** the event payload SHALL include `trigger: "lines_changed"` and `lines_changed: N`

#### Scenario: 3 minutes elapsed without snapshot
- **WHEN** 3 minutes have passed since the last snapshot AND the code has changed at all
- **THEN** the frontend SHALL emit a `code.snapshot.auto` event
- **THEN** the event payload SHALL include `trigger: "time_elapsed"` and `elapsed_ms: N`

#### Scenario: No changes since last snapshot
- **WHEN** 3 minutes have passed but the code content is identical to the last snapshot
- **THEN** the frontend SHALL NOT emit any event

### Requirement: Differentiate auto and manual snapshots in backend
The backend classifier SHALL map `code.snapshot.auto` as a distinct event type from `code.snapshot.captured` (manual). Both SHALL have `n4_level=None` (lifecycle events).

#### Scenario: Auto snapshot received by classifier
- **WHEN** a `code.snapshot.auto` event arrives
- **THEN** the classifier SHALL store it with `event_type="code.snapshot.auto"` and `n4_level=None`

#### Scenario: Manual snapshot (existing behavior preserved)
- **WHEN** a `code.snapshot.captured` event arrives
- **THEN** the classifier SHALL continue to store it as `event_type="code.snapshot"` with `n4_level=None`
