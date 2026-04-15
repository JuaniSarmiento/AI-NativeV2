## MODIFIED Requirements

### Requirement: Backend sandbox feature directory
The `backend/app/features/sandbox/` directory SHALL contain `engine.py` (subprocess execution), `runner.py` (test case runner), `schemas.py`, `router.py`.

#### Scenario: Sandbox feature importable
- **WHEN** code imports `from app.features.sandbox.engine import SandboxService`
- **THEN** the import SHALL resolve correctly

### Requirement: Student activity view with editor
The `frontend/src/features/activities/StudentActivityViewPage.tsx` SHALL include a code editor and output panel replacing the placeholder.

#### Scenario: Editor renders with starter code
- **WHEN** the student opens an exercise in an activity
- **THEN** the editor SHALL be pre-filled with the exercise's starter_code
