## 1. Database & Model Foundation

- [x] 1.1 Add `n4_level` Integer nullable column to CognitiveEvent model in `backend/app/features/cognitive/models.py`
- [x] 1.2 Add `score_breakdown` JSONB nullable column to CognitiveMetrics model in `backend/app/features/evaluation/models.py`
- [x] 1.3 Add `engine_version` String(10) column to CognitiveMetrics model
- [x] 1.4 Create Alembic migration for all new columns and B-tree index on `cognitive_events.n4_level`
- [x] 1.5 Update `CognitiveService.add_event()` to persist `n4_level` to the new column

## 2. Classifier Fixes

- [x] 2.1 Change `code.snapshot.captured` mapping from n4_level=1 to None in `classifier.py`
- [x] 2.2 Change `exercise.submitted` mapping from n4_level=2 to None in `classifier.py`
- [x] 2.3 Change `reflection.submitted` mapping from n4_level=1 to None in `classifier.py`
- [x] 2.4 Register 6 new event types in `_EVENT_TYPE_MAPPING`: problem.reading_time(1), problem.reread(1), pseudocode.written(2), code.accepted_from_tutor(4), test.manual_case(3), prompt.reformulated(4)

## 3. MetricsEngine Rewrite

- [x] 3.1 Remove `_N1_EVENT_TYPES`, `_N2_EVENT_TYPES`, `_N3_EVENT_TYPES` frozensets; implement `_events_by_level(events, level)` helper that reads `n4_level` attribute
- [x] 3.2 Rewrite `_compute_n1`: presence based on reading_time thresholds (15s/45s), depth from reread + N1 questions, quality from first-event-not-run + exploratory N1 question + reflection
- [x] 3.3 Rewrite `_compute_n2`: presence requires pseudocode.written OR N2 tutor question (not submission.created), depth from precedes-run + multiple N2 types, quality from code.run-after-pseudocode + incremental snapshots
- [x] 3.4 Update `_compute_n3`: add bonus for test.manual_case (+15 depth) and is_edge_case (+15 quality)
- [x] 3.5 Update `_compute_n4`: integrate prompt.reformulated bonus (+10), add code.accepted_from_tutor penalty (1.5x dependency when not modified)
- [x] 3.6 Rewrite `qe_verification`: measure ratio of code.snapshots followed by code.run (not num_runs/2*100)
- [x] 3.7 Fix `qe_integration`: attribute each post-tutor run to the most recent preceding tutor response only
- [x] 3.8 Fix `_derive_risk_level`: when N4=None, exclude from min_n_score calculation instead of defaulting to 100
- [x] 3.9 Fix N2 quality `distinct_types` check: require 3+ types including at least one N2-classified event
- [x] 3.10 Add `score_breakdown` generation to `compute()`: produce per-N condition arrays with {condition, met, points}
- [x] 3.11 Add `engine_version = "2.0"` to MetricsDict output

## 4. New Event Detection — Backend

- [x] 4.1 Implement pseudocode detection in consumer: analyze code.snapshot payloads for 3+ consecutive comments with control flow keywords or comment-ratio > 0.5; emit synthetic `pseudocode.written` event
- [x] 4.2 Implement test.manual_case detection in consumer: parse code.run payloads for assert/print statements with values not in exercise examples; emit synthetic `test.manual_case` event
- [x] 4.3 Implement code.accepted_from_tutor similarity detection in consumer: compare code.snapshot diffs against recent tutor response code blocks using LCS; emit if >60% match and no clipboard event within 30s
- [x] 4.4 Implement prompt.reformulated detection in tutor service: TF-IDF cosine similarity > 0.4 within 90s window, second message longer/more specific; emit event to Redis stream

## 5. New Event Emission — Frontend

- [x] 5.1 Implement `problem.reading_time` emitter: timer starts on problem view focus, emits on blur/tab-switch with duration_ms; skip if < 3000ms
- [x] 5.2 Implement `problem.reread` emitter: detect return to problem statement after code activity (check session has prior snapshot/run); emit with elapsed_since_first_read and code_lines_at_reread
- [x] 5.3 Implement `code.accepted_from_tutor` clipboard detection: intercept copy events from tutor chat code blocks; emit with fragment_length and tutor_message_id

## 6. API & Repository Changes

- [x] 6.1 Rewrite `get_commission_aggregates()` in repositories.py: use DISTINCT ON (student_id) ORDER BY computed_at DESC to get latest per student, then AVG over those
- [x] 6.2 Add `latest_temporal_coherence`, `latest_code_discourse`, `latest_inter_iteration`, `latest_appropriation_type`, `latest_score_breakdown` fields to StudentSummary schema
- [x] 6.3 Update dashboard router to populate new StudentSummary fields from latest CognitiveMetrics
- [x] 6.4 Implement `_derive_appropriation_type()` helper: >60% generative → "delegacion", exploratory>40% + verifier>10% → "reflexiva", no tutor → "autonomo", else → "superficial"
- [x] 6.5 Add `anomalies` field to trace endpoint response (extract from coherence_anomalies JSONB)
- [x] 6.6 Create new endpoint `GET /api/v1/cognitive/students/{student_id}/evolution?commission_id=X`: query CognitiveMetrics joined to CognitiveSession, filter by commission, order by started_at ASC, return [{session_id, exercise_id, exercise_title, started_at, n1, n2, n3, n4, qe, risk_level}]

## 7. Dashboard Frontend — Table & Cards

- [x] 7.1 Add mini-bars N1-N4 to student table rows: 4 small horizontal colored bars (green/yellow/red/gray) showing latest scores
- [x] 7.2 Add "Apropiacion" column with colored badge (Delegacion=red, Superficial=yellow, Reflexiva=green, Autonomo=gray)
- [x] 7.3 Add sort support for N1, N2, N3, N4 columns (click header to sort asc/desc)
- [x] 7.4 Update types.ts: add new fields to StudentSummary and DashboardData interfaces
- [x] 7.5 Display "Sin interaccion" for null N4 in all views (mini-bar, detail card, trace)

## 8. Dashboard Frontend — Student Detail

- [x] 8.1 Create ScoreBreakdown component: renders condition list with ✓/✗ icons, condition text, and point value for each N
- [x] 8.2 Create CoherenceTrafficLight component: 3 colored circles (green>=70, yellow 40-69, red<40) with labels and scores
- [x] 8.3 Integrate ScoreBreakdown into StudentDetailCard for each N-dimension
- [x] 8.4 Integrate CoherenceTrafficLight into StudentDetailCard below N-scores

## 9. Dashboard Frontend — Visualizations

- [x] 9.1 Create EvolutionChart component: line chart with 4 colored lines (N1-N4) across sessions; fetch data from evolution endpoint
- [x] 9.2 Create SwimLanesTimeline SVG component: 4 horizontal lanes, events as colored dots positioned by time, hover tooltip with event details
- [x] 9.3 Integrate EvolutionChart into StudentActivityPage (above sessions list)
- [x] 9.4 Integrate SwimLanesTimeline into expanded session detail (replace or complement existing timeline)
- [x] 9.5 Add anomaly banners to trace view: display coherence violations as warning banners above the 3-column layout

## 10. Testing & Cleanup

- [x] 10.1 Write unit tests for MetricsEngine v2: test each N-score formula with mock events covering all conditions
- [x] 10.2 Write unit tests for pseudocode detection heuristics
- [x] 10.3 Write unit tests for test.manual_case detection
- [x] 10.4 Write unit tests for prompt reformulation TF-IDF detection
- [ ] 10.5 Write integration test for dashboard endpoint with new fields
- [ ] 10.6 Write integration test for evolution endpoint
- [x] 10.7 Update knowledge-base documentation: new score formulas, new events, dashboard capabilities
