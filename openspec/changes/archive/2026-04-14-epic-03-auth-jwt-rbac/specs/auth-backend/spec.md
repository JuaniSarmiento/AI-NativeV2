## ADDED Requirements

### Requirement: Password hashing module
The system SHALL provide `backend/app/core/security.py` with functions `hash_password(plain: str) -> str` and `verify_password(plain: str, hashed: str) -> bool` using bcrypt.

#### Scenario: Hash and verify a password
- **WHEN** `hash_password("test1234")` is called and the result is passed to `verify_password("test1234", hash)`
- **THEN** `verify_password` SHALL return `True`

#### Scenario: Wrong password fails verification
- **WHEN** `verify_password("wrong", hash)` is called with a hash of "test1234"
- **THEN** it SHALL return `False`

### Requirement: JWT token creation and validation
The system SHALL provide functions `create_access_token(user_id, role, jti)` returning a JWT with `exp` of 15 minutes, and `create_refresh_token(user_id, jti)` returning a JWT with `exp` of 7 days. Both SHALL use HS256 with `SECRET_KEY` from settings. The system SHALL provide `decode_token(token) -> dict` that validates signature and expiry.

#### Scenario: Access token contains required claims
- **WHEN** an access token is created for a user
- **THEN** the decoded payload SHALL contain `sub` (user_id as string), `role`, `jti`, `exp`, and `type: "access"`

#### Scenario: Refresh token contains required claims
- **WHEN** a refresh token is created for a user
- **THEN** the decoded payload SHALL contain `sub` (user_id as string), `jti`, `exp`, and `type: "refresh"`

#### Scenario: Expired token raises error
- **WHEN** `decode_token` is called with an expired token
- **THEN** it SHALL raise an appropriate error

### Requirement: User registration endpoint
The system SHALL expose `POST /api/v1/auth/register` accepting `email`, `password`, `full_name`, and `role`. It SHALL hash the password, create the user via repository, and return user data (without password_hash).

#### Scenario: Successful registration
- **WHEN** a valid registration request is sent with a unique email
- **THEN** the system SHALL return 201 with user data and the user SHALL exist in the database

#### Scenario: Duplicate email rejected
- **WHEN** a registration request is sent with an existing email
- **THEN** the system SHALL return 409 Conflict

### Requirement: Login endpoint
The system SHALL expose `POST /api/v1/auth/login` accepting `email` and `password`. On success it SHALL return an access token in the JSON body and set a refresh token as an httpOnly cookie.

#### Scenario: Successful login
- **WHEN** valid credentials are sent
- **THEN** the system SHALL return 200 with `{ access_token, token_type: "bearer", user: {...} }` and set cookie `refresh_token` with flags `httpOnly`, `SameSite=Lax`, `Path=/api/v1/auth`

#### Scenario: Invalid credentials rejected
- **WHEN** wrong email or password is sent
- **THEN** the system SHALL return 401 with a generic "Invalid credentials" message (no leak of which field is wrong)

### Requirement: Refresh token endpoint
The system SHALL expose `POST /api/v1/auth/refresh`. It SHALL read the refresh token from the httpOnly cookie, validate it, check it is not blacklisted, blacklist the old token, and return a new access token + set a new refresh cookie (rotation).

#### Scenario: Successful refresh
- **WHEN** a valid non-blacklisted refresh token cookie is present
- **THEN** the system SHALL return 200 with a new access token, set a new refresh cookie, and blacklist the old refresh token's jti in Redis

#### Scenario: Blacklisted refresh token rejected
- **WHEN** a previously used (blacklisted) refresh token is sent
- **THEN** the system SHALL return 401

### Requirement: Logout endpoint
The system SHALL expose `POST /api/v1/auth/logout`. It SHALL blacklist both the current access token's jti and the refresh token's jti in Redis, and clear the refresh cookie.

#### Scenario: Successful logout
- **WHEN** an authenticated user calls logout
- **THEN** the system SHALL blacklist both token jtis, clear the refresh cookie, and return 200

### Requirement: Token blacklist in Redis
The system SHALL store blacklisted token jtis in Redis with key pattern `auth:blacklist:{jti}` and TTL equal to the remaining lifetime of the token. The JWT validation middleware SHALL check the blacklist before accepting a token.

#### Scenario: Blacklisted access token rejected on next request
- **WHEN** a user logs out and then sends a request with the old access token
- **THEN** the system SHALL return 401

#### Scenario: Blacklist entries auto-expire
- **WHEN** a token's TTL expires in Redis
- **THEN** the blacklist entry SHALL be automatically removed (Redis TTL)
