## MODIFIED Requirements

### Requirement: Backend exercises feature directory
The `backend/app/features/exercises/` directory SHALL contain `repositories.py`, `services.py`, `schemas.py`, `router.py`.

#### Scenario: Exercises feature importable
- **WHEN** code imports `from app.features.exercises.router import router`
- **THEN** the import SHALL resolve correctly

### Requirement: Frontend exercises feature directory
The `frontend/src/features/exercises/` directory SHALL contain exercise pages, store, and types.

#### Scenario: Exercise pages exist
- **WHEN** listing `frontend/src/features/exercises/`
- **THEN** it SHALL contain page components for exercise management and student exercise browsing
