## Why

The cognitive metrics pipeline produces inflated and misleading N1-N4 scores due to incorrect event-to-level mappings, hardcoded event type sets in MetricsEngine, and a broken aggregation strategy. The dashboard shows data that doesn't reflect actual student cognitive processes — N1 and N2 are artificially high for every student, coherence scores are invisible at the commission level, and the AVG calculation weights prolific students disproportionately. Additionally, critical cognitive events defined in the thesis (reading time, rereading, pseudocode, code acceptance from tutor, manual tests, prompt reformulation) are not captured, making it impossible to accurately measure comprehension, strategy, or AI appropriation quality.

## What Changes

### Bug Fixes (Pipeline Integrity)
- **BREAKING**: Change `code.snapshot.captured` mapping from N1 to None (lifecycle event, not comprehension)
- **BREAKING**: Change `exercise.submitted` mapping from N2 to None (mechanical act, not strategy)
- **BREAKING**: Change `reflection.submitted` mapping from N1 to None (content-dependent, needs analysis)
- Add `n4_level` column to `cognitive_events` table with index (replaces JSONB-buried field)
- Rewrite MetricsEngine to filter events by `n4_level` column instead of hardcoded event type sets
- Fix N1 calculation: remove `code.snapshot` inflation, require meaningful reading time
- Fix N2 calculation: remove `submission.created` as presence indicator, require actual strategy evidence
- Fix `qe_verification`: replace nonsensical `num_runs/2*100` with actual verification measurement
- Fix `qe_integration`: compare runs against immediately preceding tutor response, not any prior response
- Fix `_derive_risk_level`: N4=None should not default to 100 (mask bad scores in other dimensions)
- Fix N2=0 when no submission exists but strategy evidence is present
- Fix `distinct_types >= 2` quality check in N2 (trivially satisfied by any session)
- Fix commission AVG to be per-student (latest session per student) instead of per-session
- Add coherence scores + appropriation type to `StudentSummary` DTO and dashboard endpoint

### New Cognitive Events
- `problem.reading_time`: time spent reading the problem statement before coding
- `problem.reread`: student returns to problem statement after starting to code
- `pseudocode.written`: structured comments/planning detected in code snapshots
- `code.accepted_from_tutor`: code copied from tutor response (clipboard + similarity detection)
- `test.manual_case`: student writes their own test cases (asserts/prints with non-example values)
- `prompt.reformulated`: student rephrases a question within 90s with higher specificity

### Dashboard Improvements
- Mini-bars N1-N4 per student in commission table (visual profile at a glance)
- Appropriation type column (delegacion/superficial/reflexiva)
- Score breakdown with reasons (checkmarks/crosses showing what contributed to each N)
- Swim lanes timeline (events plotted by N-level over time axis)
- Coherence traffic lights in student detail
- N1-N4 evolution chart across sessions (line graph per dimension)
- Sort by individual N dimensions in student table
- "Sin interaccion" label for N4=null instead of "-"
- New endpoint: `GET /cognitive/students/{id}/evolution`

## Capabilities

### New Capabilities
- `cognitive-events-v2`: New event types (reading_time, reread, pseudocode, code_accepted, test_manual, prompt_reformulated) — emission from frontend/backend, classifier registration, MetricsEngine integration
- `metrics-engine-v2`: Rewritten score calculations for N1-N4 using n4_level column, fixed Qe sub-scores, corrected risk derivation, per-student aggregation
- `teacher-dashboard-v2`: Enhanced dashboard with mini-bars, appropriation column, coherence traffic lights, score breakdown, swim lanes, evolution chart, sorting by N dimensions

### Modified Capabilities
- `cognitive-metrics-model`: Add `n4_level` column to CognitiveEvent, add index, Alembic migration
- `evaluation-engine`: MetricsEngine rewrite — new calculation formulas for all N scores and Qe sub-scores
- `cognitive-worker`: Register 6 new event types in classifier, update consumer to handle them
- `cognitive-metrics-api`: Add coherence fields, appropriation_type, score_breakdown to StudentSummary; new evolution endpoint
- `teacher-dashboard-frontend`: Complete UI overhaul with new visualizations and interaction patterns

## Impact

### Backend
- `backend/app/features/cognitive/classifier.py` — mapping changes + 6 new event registrations
- `backend/app/features/cognitive/models.py` — new column on CognitiveEvent
- `backend/app/features/cognitive/consumer.py` — handle new event types
- `backend/app/features/evaluation/service.py` — MetricsEngine complete rewrite
- `backend/app/features/evaluation/coherence.py` — improvements to code-discourse analysis
- `backend/app/features/evaluation/repositories.py` — per-student AVG query rewrite
- `backend/app/features/evaluation/router.py` — new evolution endpoint, enriched dashboard response
- `backend/app/features/evaluation/schemas.py` — new DTOs (StudentSummary v2, ScoreBreakdown, EvolutionPoint)
- `alembic/versions/` — new migration for n4_level column + index

### Frontend
- `frontend/src/features/teacher/dashboard/TeacherDashboard.tsx` — mini-bars, appropriation, sort
- `frontend/src/features/teacher/dashboard/types.ts` — new fields
- `frontend/src/features/teacher/student/StudentActivityPage.tsx` — evolution chart, coherence, breakdown
- `frontend/src/features/teacher/trace/TracePage.tsx` — swim lanes, anomaly banners
- New components: SwimLanesTimeline, EvolutionChart, ScoreBreakdown, CoherenceTrafficLight
- Frontend event emitters for `problem.reading_time`, `problem.reread`, `code.accepted_from_tutor`

### Database
- Alembic migration: ADD COLUMN `n4_level INTEGER` on `cognitive.cognitive_events`
- CREATE INDEX on `cognitive.cognitive_events(n4_level)`
- Full database wipe (clean start, no backfill needed)

### APIs
- Modified: `GET /api/v1/teacher/courses/{id}/dashboard` — enriched response
- Modified: `GET /api/v1/cognitive/sessions/{id}/trace` — add score_breakdown, anomalies
- New: `GET /api/v1/cognitive/students/{id}/evolution` — N1-N4 per session over time
