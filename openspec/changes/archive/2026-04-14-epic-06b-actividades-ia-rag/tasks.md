## 1. Database Models + Migration

- [x] 1.1 Create `backend/app/shared/models/activity.py` with Activity model (UUID PK, course_id FK, created_by FK, title, description, prompt_used, status ENUM draft/published, is_active, timestamps)
- [x] 1.2 Create `backend/app/shared/models/llm_config.py` with LLMConfig model (UUID PK, user_id FK UNIQUE, provider ENUM openai/anthropic, api_key_encrypted TEXT, model_name, timestamps)
- [x] 1.3 Create `backend/app/core/rag/models.py` with DocumentChunk model (UUID PK, source_file, topic, chunk_index, content TEXT, embedding vector(1536), created_at)
- [x] 1.4 Add nullable `activity_id` FK to Exercise model
- [x] 1.5 Update `backend/app/shared/models/__init__.py` with new models
- [x] 1.6 Create Alembic migration: pgvector extension, activities table, llm_configs table, document_chunks table, exercises.activity_id column

## 2. LLM Adapters

- [x] 2.1 Create `backend/app/core/llm/adapters.py` with LLMAdapter protocol, OpenAIAdapter, AnthropicAdapter
- [x] 2.2 Create `backend/app/core/llm/prompts.py` with activity generation system prompt template
- [x] 2.3 Create `backend/app/core/llm/__init__.py` with factory function `get_adapter(provider, api_key)`

## 3. RAG Pipeline

- [x] 3.1 Create `backend/app/core/rag/ingest.py` with PDF parser (PyPDF2), ipynb parser (nbformat), text chunker (500 tokens, 50 overlap)
- [x] 3.2 Create `backend/app/core/rag/search.py` with `search_chunks(query, top_k)` using pgvector cosine similarity
- [x] 3.3 Create `backend/app/core/rag/__init__.py`
- [x] 3.4 Add `make ingest` target to Makefile

## 4. LLM Config Feature

- [x] 4.1 Create `backend/app/features/activities/schemas.py` with LLMConfigRequest, LLMConfigResponse, ActivityResponse, GenerateActivityRequest
- [x] 4.2 Create `backend/app/features/activities/services.py` with LLMConfigService (save/get with Fernet encryption)
- [x] 4.3 Add LLM config endpoints to router: GET/PUT /api/v1/settings/llm

## 5. Activity Generation Service

- [x] 5.1 Create `backend/app/features/activities/generation.py` with ActivityGenerationService (RAG search → prompt construction → LLM call → parse JSON → create Activity + Exercises draft)
- [x] 5.2 Add generation endpoint: POST /api/v1/activities/generate
- [x] 5.3 Add Activity CRUD endpoints: GET list, GET detail, PUT update, POST publish, DELETE

## 6. Activity Router Registration

- [x] 6.1 Create `backend/app/features/activities/router.py` aggregating all endpoints
- [x] 6.2 Register activities router in `backend/app/main.py`

## 7. Dependencies

- [x] 7.1 Add to pyproject.toml: `openai`, `anthropic`, `PyPDF2`, `nbformat`, `pgvector`, `cryptography`

## 8. Frontend — Settings

- [x] 8.1 Create `frontend/src/features/activities/types.ts` with Activity, LLMConfig types
- [x] 8.2 Create `frontend/src/features/activities/store.ts` with useActivitiesStore (Zustand 5)
- [x] 8.3 Create `frontend/src/features/activities/SettingsLLMPage.tsx` — API key config (provider select, key input, model name)

## 9. Frontend — Generation + Review

- [x] 9.1 Create `frontend/src/features/activities/GenerateActivityPage.tsx` — chat-like interface, prompt input, loading state, result display
- [x] 9.2 Create `frontend/src/features/activities/ActivityDetailPage.tsx` — review draft exercises, edit inline, publish button
- [x] 9.3 Create `frontend/src/features/activities/ActivitiesPage.tsx` — list activities (draft/published)

## 10. App Integration

- [x] 10.1 Update `frontend/src/App.tsx` with activity routes (/activities, /activities/new, /activities/:id)
- [x] 10.2 Update `frontend/src/shared/lib/navigation.ts` with activities nav items for docente
- [x] 10.3 Add settings route for LLM config

## 11. Tests

- [x] 11.1 Create `backend/tests/unit/test_llm_adapters.py` with mock tests for OpenAI and Anthropic adapters
- [x] 11.2 Create `backend/tests/integration/test_activities.py` with tests for CRUD, publish, generation (mocked LLM)
