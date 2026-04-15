## MODIFIED Requirements

### Requirement: Backend courses feature directory
The `backend/app/features/courses/` directory SHALL contain `models.py`, `repositories.py`, `services.py`, `schemas.py`, `router.py`.

#### Scenario: Courses feature is importable
- **WHEN** code imports `from app.features.courses.router import router`
- **THEN** the import SHALL resolve correctly

### Requirement: Frontend courses feature directory
The `frontend/src/features/courses/` directory SHALL contain course pages, commission components, stores, and types.

#### Scenario: Courses pages exist
- **WHEN** listing `frontend/src/features/courses/`
- **THEN** it SHALL contain at minimum page components for course management and student enrollment
