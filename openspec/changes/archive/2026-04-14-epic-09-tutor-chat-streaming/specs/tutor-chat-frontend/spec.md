## ADDED Requirements

### Requirement: TutorChat component
The system SHALL provide a `TutorChat` component that renders a chat interface between the alumno and tutor. It SHALL use the existing design system components (Card, Button, Input).

#### Scenario: Chat displays message history
- **WHEN** the TutorChat component mounts with an active exercise
- **THEN** it SHALL display the conversation history with alumno messages aligned right and tutor messages aligned left, inside a Card component

#### Scenario: Streaming tokens render progressively
- **WHEN** the tutor is responding
- **THEN** tokens SHALL appear one by one in the current tutor message bubble, with a blinking cursor indicator

#### Scenario: Typing indicator while waiting
- **WHEN** the alumno sends a message and the tutor has not started responding
- **THEN** a "El tutor está escribiendo..." indicator SHALL be visible

#### Scenario: Message input with send
- **WHEN** the alumno types in the input and presses Enter
- **THEN** the message SHALL be sent via WebSocket and the input cleared. Shift+Enter SHALL insert a newline.

#### Scenario: Rate limit display
- **WHEN** a `rate_limit` message is received
- **THEN** the remaining message count SHALL be displayed subtly near the input. When 0, the input SHALL be disabled with a message showing `reset_at`.

### Requirement: WebSocket connection management with ref pattern
The system SHALL manage the WebSocket connection using `useRef` with two separate `useEffect` hooks — one for connection lifecycle, one for message handling.

#### Scenario: Connection established on mount
- **WHEN** the TutorChat component mounts
- **THEN** a WebSocket connection SHALL be established to `ws://api/ws/tutor/chat?token=<JWT>`

#### Scenario: Cleanup on unmount
- **WHEN** the TutorChat component unmounts
- **THEN** the WebSocket connection SHALL be closed cleanly

#### Scenario: Reconnection with exponential backoff
- **WHEN** the WebSocket connection drops
- **THEN** the system SHALL attempt reconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s) and display a "Reconectando..." indicator

#### Scenario: History loaded on reconnect
- **WHEN** the WebSocket reconnects after a drop
- **THEN** the system SHALL fetch message history via REST fallback to restore the conversation state

### Requirement: useTutorStore Zustand store
The system SHALL provide a `useTutorStore` for managing tutor chat state with individual selectors.

#### Scenario: Messages updated via store actions
- **WHEN** a new message (alumno or tutor) arrives
- **THEN** it SHALL be added to the store via an action, never via direct setState

#### Scenario: Individual selectors prevent rerenders
- **WHEN** a component reads `useTutorStore(s => s.messages)`
- **THEN** it SHALL only rerender when the messages array reference changes, using `useShallow` for array comparison

#### Scenario: Store scoped to current exercise
- **WHEN** the alumno navigates to a different exercise
- **THEN** the store SHALL clear the current messages and load the new exercise's session

### Requirement: Integration in exercise view
The TutorChat SHALL be integrated as a right panel in the exercise view, alongside the Monaco editor.

#### Scenario: Desktop layout with side panel
- **WHEN** the viewport is wider than 1024px
- **THEN** the TutorChat SHALL render as a resizable right panel next to the code editor

#### Scenario: Mobile layout with bottom sheet
- **WHEN** the viewport is narrower than 1024px
- **THEN** the TutorChat SHALL render as a collapsible bottom sheet with a handle, expandable to full height
