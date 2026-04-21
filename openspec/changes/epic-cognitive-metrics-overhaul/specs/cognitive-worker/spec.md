## MODIFIED Requirements

### Requirement: Classifier event type mapping
The CognitiveEventClassifier mapping SHALL assign n4_level as follows:

| Raw event type | Canonical type | n4_level |
|---|---|---|
| reads_problem | reads_problem | 1 |
| code.executed | code.run | 3 |
| code.execution.failed | code.run | 3 |
| code.snapshot.captured | code.snapshot | None |
| exercise.submitted | submission.created | None |
| tutor.session.started | session.started | None |
| tutor.session.ended | session.closed | None |
| reflection.submitted | reflection.submitted | None |
| problem.reading_time | problem.reading_time | 1 |
| problem.reread | problem.reread | 1 |
| pseudocode.written | pseudocode.written | 2 |
| code.accepted_from_tutor | code.accepted_from_tutor | 4 |
| test.manual_case | test.manual_case | 3 |
| prompt.reformulated | prompt.reformulated | 4 |

#### Scenario: code.snapshot classified as None
- **WHEN** classifier receives `code.snapshot.captured`
- **THEN** it returns ClassifiedEvent with n4_level=None (not 1)

#### Scenario: exercise.submitted classified as None
- **WHEN** classifier receives `exercise.submitted`
- **THEN** it returns ClassifiedEvent with n4_level=None (not 2)

#### Scenario: New event pseudocode.written
- **WHEN** classifier receives `pseudocode.written`
- **THEN** it returns ClassifiedEvent with event_type="pseudocode.written", n4_level=2

### Requirement: Consumer persists n4_level to column
The CognitiveEventConsumer SHALL pass the classified `n4_level` to `CognitiveService.add_event()` which SHALL persist it to the new `n4_level` column on CognitiveEvent.

#### Scenario: Event with level persisted
- **WHEN** consumer processes a classified event with n4_level=3
- **THEN** the CognitiveEvent row has column `n4_level=3` AND payload still contains `n4_level: 3`

#### Scenario: Lifecycle event persisted
- **WHEN** consumer processes a session.started event with n4_level=None
- **THEN** the CognitiveEvent row has column `n4_level=NULL`

## ADDED Requirements

### Requirement: Pseudocode detection in snapshot processing
The consumer SHALL analyze `code.snapshot.captured` events to detect pseudocode patterns and emit a synthetic `pseudocode.written` event when detected.

#### Scenario: Snapshot contains pseudocode
- **WHEN** consumer processes a code.snapshot.captured with 4 consecutive comment lines containing "primero", "luego"
- **THEN** consumer emits an additional `pseudocode.written` event to the same session

#### Scenario: Snapshot contains normal code comments
- **WHEN** consumer processes a code.snapshot.captured with 1 comment line
- **THEN** no additional event is emitted

### Requirement: Manual test detection in code.run processing
The consumer SHALL analyze `code.executed` / `code.execution.failed` events to detect manual test cases and emit a synthetic `test.manual_case` event when detected.

#### Scenario: Executed code contains custom asserts
- **WHEN** consumer processes code.executed with `assert func([3,2,1]) == 1` where `[3,2,1]` is not in exercise examples
- **THEN** consumer emits `test.manual_case` event with appropriate payload

### Requirement: Code acceptance detection via similarity
The consumer SHALL compare code.snapshot diffs against recent tutor responses (last 5 minutes) using LCS similarity. If similarity exceeds 60% and no clipboard-based event exists within 30 seconds, emit `code.accepted_from_tutor`.

#### Scenario: High similarity detected
- **WHEN** snapshot diff matches 70% of a tutor code block from 2 minutes ago
- **THEN** consumer emits `code.accepted_from_tutor` with detection_method="similarity"

#### Scenario: Clipboard event already exists
- **WHEN** frontend already emitted code.accepted_from_tutor via clipboard 10 seconds ago for same content
- **THEN** consumer does NOT emit duplicate event
