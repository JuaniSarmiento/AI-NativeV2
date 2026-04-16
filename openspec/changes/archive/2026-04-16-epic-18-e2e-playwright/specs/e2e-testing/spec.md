## ADDED Requirements

### Requirement: Playwright setup
The system SHALL have Playwright configured with chromium browser, base URL pointing to localhost:5173, and a global setup that ensures the app is running.

#### Scenario: Playwright runs
- **WHEN** `npx playwright test` is executed
- **THEN** tests SHALL run against the local dev environment

### Requirement: Alumno E2E flow
The system SHALL have an E2E test covering: register alumno → login → enroll in commission → open activity → write code → execute → submit → reflection.

#### Scenario: Full alumno flow passes
- **WHEN** the alumno E2E test runs
- **THEN** all steps SHALL complete without errors

### Requirement: Docente E2E flow
The system SHALL have an E2E test covering: login docente → see courses → open course → see submissions → evaluate with AI → confirm grade.

#### Scenario: Full docente flow passes
- **WHEN** the docente E2E test runs with existing student submission
- **THEN** all steps SHALL complete without errors

### Requirement: RBAC security tests
The system SHALL have tests verifying: unauthenticated request gets 401, alumno accessing teacher endpoint gets 403.

#### Scenario: Security checks pass
- **WHEN** security E2E tests run
- **THEN** correct HTTP status codes SHALL be returned
