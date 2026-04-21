## 1. Database & Model

- [x] 1.1 Create SQLAlchemy model `CognitiveReport` in `app/features/reports/models.py` (schema: cognitive)
- [x] 1.2 Create Alembic migration for `cognitive.cognitive_reports` table
- [x] 1.3 Create `CognitiveReportRepository` in `app/features/reports/repository.py`

## 2. Analytical Engine

- [x] 2.1 Create `app/features/reports/analytical.py` with `build_structured_analysis()` function
- [x] 2.2 Implement score aggregation (avg N1-N4, Qe across sessions)
- [x] 2.3 Implement pattern detection (high_ai_dependency, low_validation, tutor_copy_paste)
- [x] 2.4 Implement strengths/weaknesses extraction from scores and events
- [x] 2.5 Implement evolution trend (compare first vs last session metrics)
- [x] 2.6 Implement data_hash computation (SHA-256 of deterministic JSON)

## 3. Narrative Engine

- [x] 3.1 Create `app/features/reports/narrative.py` with system prompt and `generate_narrative()` function
- [x] 3.2 Write the pedagogical system prompt (anti-hallucination, section format, Spanish)
- [x] 3.3 Integrate with AI Gateway (`get_adapter` + docente's `LLMConfig`)

## 4. Service & Router

- [x] 4.1 Create `app/features/reports/schemas.py` (GenerateReportRequest, ReportResponse)
- [x] 4.2 Create `app/features/reports/service.py` orchestrating analytical → cache check → narrative → persist
- [x] 4.3 Create `app/features/reports/router.py` with POST /generate, GET /{id}, GET / (query)
- [x] 4.4 Register router in `app/main.py`

## 5. Frontend

- [x] 5.1 Create `features/teacher/reports/ReportView.tsx` component (renders Markdown, loading, error states)
- [x] 5.2 Add "Ver Informe" button in `StudentActivityPage.tsx` for each student with sessions
- [x] 5.3 Create route `/teacher/reports/:studentId/:activityId` and wire navigation
- [x] 5.4 API call: POST to generate, GET to fetch cached, display result

## 6. Integration & Testing

- [x] 6.1 Manual end-to-end test: docente generates report for a student with sessions
- [x] 6.2 Verify cache hit: second request returns cached report without LLM call
- [x] 6.3 Verify error handling: no sessions, invalid API key, missing LLM config
