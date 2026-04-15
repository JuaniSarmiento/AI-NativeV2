## MODIFIED Requirements

### Requirement: Backend submissions feature directory
The `backend/app/features/submissions/` directory SHALL contain models.py, services.py, schemas.py, router.py.

#### Scenario: Submissions feature importable
- **WHEN** code imports `from app.features.submissions.router import router`
- **THEN** the import SHALL resolve correctly
