## MODIFIED Requirements

### Requirement: Backend shared models directory
The `backend/app/shared/models/` directory SHALL contain one Python file per domain model. An `__init__.py` SHALL re-export all models for convenient importing.

#### Scenario: Models are importable from shared.models
- **WHEN** code imports `from app.shared.models import User, Course, Commission`
- **THEN** the imports SHALL resolve correctly

### Requirement: Backend shared repositories directory
The `backend/app/shared/repositories/` directory SHALL contain the `base.py` file with `BaseRepository` and an `__init__.py` that re-exports it.

#### Scenario: BaseRepository is importable
- **WHEN** code imports `from app.shared.repositories import BaseRepository`
- **THEN** the import SHALL resolve correctly

### Requirement: Seed data directory
The `infra/seed/` directory SHALL contain seed scripts and a runner module.

#### Scenario: Seed directory structure
- **WHEN** listing `infra/seed/`
- **THEN** it SHALL contain at minimum: `__init__.py`, `runner.py`, `01_base_data.py`
