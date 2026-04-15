## MODIFIED Requirements

### Requirement: Backend auth feature directory
The `backend/app/features/auth/` directory SHALL contain `router.py`, `schemas.py`, `service.py`, and `dependencies.py`.

#### Scenario: Auth feature is importable
- **WHEN** code imports `from app.features.auth.router import router`
- **THEN** the import SHALL resolve correctly

### Requirement: Backend core security module
The `backend/app/core/security.py` SHALL exist with password hashing and JWT utilities.

#### Scenario: Security module is importable
- **WHEN** code imports `from app.core.security import hash_password, verify_password, create_access_token`
- **THEN** the imports SHALL resolve correctly

### Requirement: Frontend auth feature directory
The `frontend/src/features/auth/` directory SHALL contain login page, register page, auth store, protected route component, and types.

#### Scenario: Auth store is importable
- **WHEN** code imports `import { useAuthStore } from '@/features/auth/store'`
- **THEN** the import SHALL resolve correctly
