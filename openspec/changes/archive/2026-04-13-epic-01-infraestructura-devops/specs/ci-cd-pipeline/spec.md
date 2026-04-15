## ADDED Requirements

### Requirement: GitHub Actions CI pipeline
A GitHub Actions workflow SHALL run on every pull request to the `master` branch, executing lint, tests, and build checks.

#### Scenario: PR triggers CI
- **WHEN** a developer opens or updates a pull request targeting `master`
- **THEN** the CI workflow SHALL trigger and run all checks

#### Scenario: CI blocks merge on failure
- **WHEN** any CI check fails (lint, tests, or build)
- **THEN** the PR SHALL be marked as failing and merge SHALL be blocked

### Requirement: Backend linting with ruff and mypy
The CI pipeline SHALL run `ruff check` and `mypy` on the `backend/` directory.

#### Scenario: Ruff catches style violations
- **WHEN** the backend code contains ruff rule violations
- **THEN** the lint step SHALL fail and report the violations

#### Scenario: Mypy catches type errors
- **WHEN** the backend code contains type annotation errors
- **THEN** the mypy step SHALL fail and report the errors

### Requirement: Frontend linting with ESLint and Prettier
The CI pipeline SHALL run `eslint` and `prettier --check` on the `frontend/` directory.

#### Scenario: ESLint catches code issues
- **WHEN** the frontend code contains ESLint rule violations
- **THEN** the lint step SHALL fail and report the violations

#### Scenario: Prettier catches formatting issues
- **WHEN** the frontend code has inconsistent formatting
- **THEN** the prettier check SHALL fail

### Requirement: Backend tests with pytest
The CI pipeline SHALL run `pytest` with the `--tb=short` flag on the `backend/tests/` directory.

#### Scenario: Tests pass
- **WHEN** all pytest tests pass
- **THEN** the test step SHALL succeed and report the number of tests run

#### Scenario: Tests fail
- **WHEN** any pytest test fails
- **THEN** the test step SHALL fail and report the failure details

### Requirement: Frontend tests with vitest
The CI pipeline SHALL run `vitest run` on the `frontend/` directory.

#### Scenario: Vitest runs successfully
- **WHEN** all vitest tests pass
- **THEN** the test step SHALL succeed

### Requirement: Build verification
The CI pipeline SHALL verify that the backend can start (import check) and the frontend can build (`vite build`).

#### Scenario: Frontend build succeeds
- **WHEN** the frontend code compiles without errors
- **THEN** the build step SHALL produce a `dist/` directory and succeed

#### Scenario: Backend import check succeeds
- **WHEN** all backend modules can be imported without errors
- **THEN** the build check SHALL succeed
