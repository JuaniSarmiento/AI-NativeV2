## ADDED Requirements

### Requirement: get_current_user dependency
The system SHALL provide a FastAPI dependency `get_current_user` that extracts the JWT from the `Authorization: Bearer <token>` header, validates it (signature, expiry, blacklist), and returns the User model instance. If invalid, it SHALL raise 401.

#### Scenario: Valid token returns user
- **WHEN** a request with a valid access token is made
- **THEN** `get_current_user` SHALL return the User instance with id, email, role, full_name

#### Scenario: Missing token returns 401
- **WHEN** a request without Authorization header is made to a protected endpoint
- **THEN** the system SHALL return 401 with code "UNAUTHORIZED"

#### Scenario: Invalid token returns 401
- **WHEN** a request with a malformed or expired token is made
- **THEN** the system SHALL return 401

### Requirement: require_role dependency
The system SHALL provide a dependency factory `require_role(*roles: str)` that checks the current user's role against the allowed roles. If the user's role is not in the allowed list, it SHALL raise 403.

#### Scenario: Matching role passes
- **WHEN** a docente accesses an endpoint with `require_role("docente", "admin")`
- **THEN** the request SHALL proceed normally

#### Scenario: Non-matching role returns 403
- **WHEN** an alumno accesses an endpoint with `require_role("docente")`
- **THEN** the system SHALL return 403 with code "FORBIDDEN"

### Requirement: Rate limiting middleware
The system SHALL apply rate limiting of 100 requests per minute per IP address globally. Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) SHALL be included in responses.

#### Scenario: Under rate limit
- **WHEN** a client sends fewer than 100 requests per minute
- **THEN** all requests SHALL succeed and include rate limit headers

#### Scenario: Over rate limit
- **WHEN** a client exceeds 100 requests per minute
- **THEN** the system SHALL return 429 Too Many Requests
