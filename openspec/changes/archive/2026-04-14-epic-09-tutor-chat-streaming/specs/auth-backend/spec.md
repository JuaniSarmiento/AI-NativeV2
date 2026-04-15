## MODIFIED Requirements

### Requirement: JWT validation for WebSocket handshake
The auth module SHALL expose a reusable `validate_ws_token(token: str) -> UserPayload` function that validates a JWT from a WebSocket query param, separate from the HTTP middleware dependency.

#### Scenario: Valid token returns user payload
- **WHEN** `validate_ws_token` is called with a valid, non-expired JWT
- **THEN** it SHALL return the decoded user payload (user_id, role, email)

#### Scenario: Expired token raises
- **WHEN** `validate_ws_token` is called with an expired JWT
- **THEN** it SHALL raise `AuthenticationError`

#### Scenario: Blacklisted token raises
- **WHEN** `validate_ws_token` is called with a JTI present in Redis blacklist
- **THEN** it SHALL raise `AuthenticationError`
