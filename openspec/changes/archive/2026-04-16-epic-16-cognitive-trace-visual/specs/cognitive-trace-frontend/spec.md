## ADDED Requirements

### Requirement: Trace page route
The system SHALL provide a page at route `/teacher/trace/:sessionId` that displays the full cognitive trace for a session. The page SHALL be accessible to docente and admin roles.

#### Scenario: Navigation to trace
- **WHEN** a docente clicks a session row in the dashboard or student profile
- **THEN** the browser SHALL navigate to `/teacher/trace/{sessionId}`

### Requirement: Timeline component
The system SHALL render a vertical timeline of CTR events, each color-coded by N4 level: N1=blue (--color-info-500), N2=green (--color-success-500), N3=orange (--color-warning-500), N4=purple (--color-accent-500). Events without N4 classification SHALL use neutral color. Each timeline node SHALL show: event type (Spanish label), timestamp, and a brief summary from the payload.

#### Scenario: Color-coded events
- **WHEN** an event has n4_level 3 (validacion)
- **THEN** the timeline node SHALL use orange color (--color-warning-500)

#### Scenario: Event summary
- **WHEN** a tutor.question_asked event is rendered
- **THEN** the timeline node SHALL show "Pregunta al tutor" with a truncated preview of the question

### Requirement: Code evolution panel
The system SHALL render a panel showing code snapshots as a scrollable list. Each snapshot SHALL display: timestamp, and the code text. When two consecutive snapshots exist, the system SHALL show a diff view highlighting additions (green) and deletions (red). Diffs SHALL be computed in the frontend.

#### Scenario: Diff between snapshots
- **WHEN** two consecutive snapshots have different code
- **THEN** the panel SHALL display a diff with green lines for additions and red lines for deletions

#### Scenario: Single snapshot
- **WHEN** only one snapshot exists
- **THEN** the panel SHALL display the code without diff

### Requirement: Chat panel
The system SHALL render the tutor chat history for the session's exercise. Messages SHALL be fetched from `GET /api/v1/tutor/sessions/{exercise_id}/messages`. The panel SHALL display user and assistant messages in a conversation layout matching the existing ChatMessage component style.

#### Scenario: Chat loads for session
- **WHEN** the trace page loads
- **THEN** the chat panel SHALL fetch and display all tutor messages for the exercise

### Requirement: Metrics summary card
The system SHALL display the session's cognitive metrics (N1-N4 scores, Qe, dependency, risk level) in a compact card at the top of the trace page. If metrics have not been computed, the card SHALL show "Metricas pendientes".

#### Scenario: Metrics available
- **WHEN** the session has computed metrics
- **THEN** the card SHALL display N1-N4 scores with labels and a risk badge

#### Scenario: Metrics not available
- **WHEN** the session is still open or metrics not computed
- **THEN** the card SHALL show "Metricas pendientes"

### Requirement: Hash chain integrity indicator
The system SHALL display an integrity indicator showing whether the CTR hash chain is valid. The indicator SHALL call the existing verify endpoint. A green checkmark for valid, red alert for compromised.

#### Scenario: Valid chain
- **WHEN** verification returns valid=true
- **THEN** a green checkmark with "Cadena integra" SHALL be displayed

#### Scenario: Compromised chain
- **WHEN** verification returns valid=false
- **THEN** a red alert with "Cadena comprometida en evento #{sequence}" SHALL be displayed

### Requirement: Trace store
The system SHALL provide a `useTraceStore` Zustand store with: `session`, `events`, `metrics`, `verification`, `snapshots`, `chatMessages`, `isLoading`, `error`, `fetchTrace(sessionId)` action. The store SHALL follow individual selector pattern and clear state on unmount.

#### Scenario: Fetch trace loads all data
- **WHEN** `fetchTrace` is called
- **THEN** the store SHALL call trace, code-evolution, and chat endpoints in parallel and populate all fields
