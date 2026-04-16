## 1. Models & Migration

- [x] 1.1 Create `CognitiveMetrics` SQLAlchemy model in `app/features/evaluation/models.py` with all NUMERIC fields, UNIQUE constraint on session_id, and indexes
- [x] 1.2 Create `ReasoningRecord` SQLAlchemy model in `app/features/evaluation/models.py` with hash chain fields and session_id index
- [x] 1.3 Create Alembic migration `013_add_cognitive_metrics_and_reasoning_records.py` for both tables in cognitive schema
- [x] 1.4 Register models in `app/shared/models/__init__.py`

## 2. Rubric & Configuration

- [x] 2.1 Create `rubrics/n4_anexo_b.yaml` with default weights, risk thresholds, and quality factors
- [x] 2.2 Create `app/features/evaluation/rubric.py` — load and parse YAML, fallback to defaults if file missing

## 3. MetricsEngine (Pure Computation)

- [x] 3.1 Create `app/features/evaluation/service.py` with `MetricsEngine` class — constructor takes rubric config
- [x] 3.2 Implement N1-N4 score computation methods (event counting + quality factors, 0-100 NUMERIC)
- [x] 3.3 Implement Qe computation (4 sub-scores: quality_prompt, critical_evaluation, integration, verification)
- [x] 3.4 Implement help_seeking_ratio, autonomy_index, dependency_score computation
- [x] 3.5 Implement risk_level derivation (critical → high → medium → low)
- [x] 3.6 Implement `E = f(N1, N2, N3, N4, Qe)` — weighted profile JSONB generation
- [x] 3.7 Implement ReasoningRecord creation with hash chain (evidence of computation)

## 4. Integration with CognitiveService

- [x] 4.1 Create `app/features/evaluation/repositories.py` — `CognitiveMetricsRepository` with get_by_session, get_by_student, get_commission_aggregates
- [x] 4.2 Modify `CognitiveService.close_session()` to call MetricsEngine after sealing hash chain, persist CognitiveMetrics + n4_final_score
- [x] 4.3 Ensure consumer and timeout checker both trigger metrics computation via the updated close_session flow

## 5. REST Endpoints

- [x] 5.1 Create `app/features/evaluation/schemas.py` — Pydantic DTOs for all 4 endpoints
- [x] 5.2 Create `app/features/evaluation/router.py` — GET /api/v1/cognitive/sessions/{id}/metrics (docente/admin)
- [x] 5.3 Implement GET /api/v1/teacher/courses/{id}/dashboard with commission_id query param, exercise_id filter
- [x] 5.4 Implement GET /api/v1/teacher/students/{id}/profile with aggregated metrics and trends
- [x] 5.5 Implement GET /api/v1/student/me/progress with anti-gaming data restriction
- [x] 5.6 Register router in `app/main.py`

## 6. Backend Tests

- [x] 6.1 Unit tests for MetricsEngine — deterministic scoring with known event sets
- [x] 6.2 Unit tests for N1-N4 edge cases (empty session, single event type, all events one level)
- [x] 6.3 Unit tests for Qe computation (no tutor interactions, high verification, zero verification)
- [x] 6.4 Unit tests for risk level derivation (all 4 levels)
- [x] 6.5 Unit tests for ReasoningRecord hash chain integrity
- [x] 6.6 Unit tests for rubric loading (file present, file missing → defaults)

## 7. Frontend — Teacher Dashboard

- [x] 7.1 Install Recharts dependency
- [x] 7.2 Create Zustand store `useTeacherDashboardStore` with commission metrics, student list, filters
- [x] 7.3 Create `TeacherDashboard` page component at `/teacher/courses/:courseId/dashboard`
- [x] 7.4 Create `N4RadarChart` component with Recharts RadarChart — commission average + student overlay
- [x] 7.5 Create `StudentScoresTable` component with sortable columns and risk level filter
- [x] 7.6 Create `RiskDistributionCard` component with color-coded indicators
- [x] 7.7 Add commission selector and exercise filter controls
- [x] 7.8 Add route to App.tsx router

## 8. Frontend — Student Progress

- [x] 8.1 Create Zustand store `useStudentProgressStore` with aggregated scores and evolution data
- [x] 8.2 Create `StudentProgress` page component at `/student/progress`
- [x] 8.3 Create `EvolutionChart` component with Recharts LineChart — N1-N4 over time
- [x] 8.4 Create `ScoreCard` component — dimension name, current score, trend indicator
- [x] 8.5 Create empty state for no sessions
- [x] 8.6 Add route to App.tsx router
