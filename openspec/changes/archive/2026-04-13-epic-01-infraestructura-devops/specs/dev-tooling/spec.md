## ADDED Requirements

### Requirement: Makefile with convenience targets
A `Makefile` at the project root SHALL provide targets for common development tasks.

#### Scenario: make dev starts development environment
- **WHEN** a developer runs `make dev`
- **THEN** Docker Compose SHALL start all services in detached mode

#### Scenario: make test runs all tests
- **WHEN** a developer runs `make test`
- **THEN** both backend (pytest) and frontend (vitest) test suites SHALL run

#### Scenario: make seed populates initial data
- **WHEN** a developer runs `make seed`
- **THEN** the database SHALL be populated with seed data for development

#### Scenario: make lint runs all linters
- **WHEN** a developer runs `make lint`
- **THEN** ruff, mypy, eslint, and prettier SHALL run on their respective directories

#### Scenario: make down stops all services
- **WHEN** a developer runs `make down`
- **THEN** all Docker Compose services SHALL stop

#### Scenario: make migrate runs database migrations
- **WHEN** a developer runs `make migrate`
- **THEN** Alembic SHALL apply pending migrations to the database

### Requirement: Pre-commit hooks for code quality
Pre-commit hooks SHALL be configured to run linters and formatters on staged files before each commit.

#### Scenario: Pre-commit runs ruff on Python files
- **WHEN** a developer commits changes to `.py` files
- **THEN** ruff SHALL check and auto-format the staged Python files

#### Scenario: Pre-commit runs mypy on Python files
- **WHEN** a developer commits changes to `.py` files
- **THEN** mypy SHALL type-check the staged Python files

#### Scenario: Pre-commit runs ESLint on TypeScript files
- **WHEN** a developer commits changes to `.ts` or `.tsx` files
- **THEN** ESLint SHALL check the staged files

#### Scenario: Pre-commit runs Prettier on frontend files
- **WHEN** a developer commits changes to `.ts`, `.tsx`, `.css`, or `.json` files
- **THEN** Prettier SHALL check formatting on the staged files

### Requirement: Complete env.example
The `env.example` file SHALL document every environment variable required by the project with sensible defaults for local development.

#### Scenario: env.example has all variables
- **WHEN** a developer reads `env.example`
- **THEN** it SHALL contain at minimum: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `SECRET_KEY`, and any service-specific variables with comments explaining their purpose

### Requirement: Seed data scripts
Seed data scripts SHALL populate the database with realistic development data.

#### Scenario: Seed creates base data
- **WHEN** seed data is applied to a fresh database
- **THEN** it SHALL create sample courses, commissions, students, and exercises sufficient for development and manual testing
