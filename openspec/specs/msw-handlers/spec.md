## ADDED Requirements

### Requirement: MSW browser worker setup
The system SHALL provide MSW configuration at `frontend/src/mocks/browser.ts` that starts the service worker. It SHALL be activated conditionally only when `VITE_ENABLE_MSW=true`.

#### Scenario: MSW disabled by default
- **WHEN** the app starts without `VITE_ENABLE_MSW=true`
- **THEN** MSW SHALL NOT intercept any requests

#### Scenario: MSW enabled via env var
- **WHEN** `VITE_ENABLE_MSW=true` is set
- **THEN** MSW SHALL intercept matching requests and return mock data

### Requirement: Auth mock handlers
The system SHALL provide mock handlers for `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `POST /api/v1/auth/refresh`, and `POST /api/v1/auth/logout` returning realistic mock data.

#### Scenario: Mock login returns token
- **WHEN** MSW is active and login is called with any credentials
- **THEN** the handler SHALL return a mock access_token and user object
