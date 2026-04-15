## MODIFIED Requirements

### Requirement: Backend activities feature directory
The `backend/app/features/activities/` directory SHALL contain models.py, schemas.py, services.py, router.py for activity CRUD and generation.

#### Scenario: Activities feature importable
- **WHEN** code imports `from app.features.activities.router import router`
- **THEN** the import SHALL resolve correctly

### Requirement: Backend RAG and LLM core modules
The `backend/app/core/rag/` directory SHALL contain ingest.py (document processing), search.py (semantic search). The `backend/app/core/llm/` directory SHALL contain adapters.py (LLM protocol + implementations), prompts.py (generation prompt templates).

#### Scenario: RAG search importable
- **WHEN** code imports `from app.core.rag.search import search_chunks`
- **THEN** the import SHALL resolve correctly

### Requirement: Frontend activities feature directory
The `frontend/src/features/activities/` directory SHALL contain generation chat, activity review, and settings components.

#### Scenario: Activities pages exist
- **WHEN** listing frontend/src/features/activities/
- **THEN** it SHALL contain generation and review page components
