## MODIFIED Requirements

### Requirement: Shared components directory
The `frontend/src/shared/components/` directory SHALL contain Button.tsx, Input.tsx, Card.tsx, Modal.tsx.

#### Scenario: Components are importable
- **WHEN** code imports `from '@/shared/components/Button'`
- **THEN** the import SHALL resolve correctly

### Requirement: Mocks directory
The `frontend/src/mocks/` directory SHALL contain `browser.ts`, `handlers/index.ts`, `handlers/auth.ts`.

#### Scenario: MSW is importable
- **WHEN** code imports `from '@/mocks/browser'`
- **THEN** the import SHALL resolve correctly

### Requirement: Backend shared schemas directory
The `backend/app/shared/schemas/` directory SHALL contain `response.py` with StandardResponse and PaginatedResponse.

#### Scenario: Response schemas importable
- **WHEN** code imports `from app.shared.schemas.response import StandardResponse`
- **THEN** the import SHALL resolve correctly
