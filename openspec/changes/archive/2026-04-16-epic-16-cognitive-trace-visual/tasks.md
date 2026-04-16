## 1. Backend — Cognitive Trace Endpoints

- [x] 1.1 Add `get_sessions_by_commission(commission_id, student_id, exercise_id, status, page, per_page)` method to `CognitiveSessionRepository`
- [x] 1.2 Add `GET /api/v1/cognitive/sessions` list endpoint with commission_id, student_id, exercise_id, status filters and pagination. Requires docente/admin
- [x] 1.3 Create `TraceResponse` schema in `cognitive/schemas.py` — session + events + metrics + verification in one DTO
- [x] 1.4 Add `GET /api/v1/cognitive/sessions/{session_id}/trace` endpoint that returns unified trace (session, events, metrics, verify result). Requires docente/admin
- [x] 1.5 Create `TimelineEventResponse` schema with event fields + n4_level extracted from payload
- [x] 1.6 Add `GET /api/v1/cognitive/sessions/{session_id}/timeline` endpoint with pagination. Requires docente/admin
- [x] 1.7 Create `CodeEvolutionResponse` schema — list of {snapshot_id, code, timestamp}
- [x] 1.8 Add `GET /api/v1/cognitive/sessions/{session_id}/code-evolution` endpoint that joins cognitive events (code.snapshot) with operational.code_snapshots via snapshot_id in payload. Requires docente/admin

## 2. Backend — Governance Prompts Endpoint

- [x] 2.1 Create `PromptHistoryResponse` schema in `governance/schemas.py` — id, name, version, sha256_hash, is_active, created_at
- [x] 2.2 Add `list_prompts(page, per_page)` method to `TutorPromptRepository` or GovernanceService
- [x] 2.3 Add `GET /api/v1/governance/prompts` endpoint. Requires admin

## 3. Frontend — Trace Store + Types

- [x] 3.1 Create `frontend/src/features/teacher/trace/types.ts` with TraceSession, TraceEvent, TraceMetrics, CodeSnapshot, ChatMessage, VerifyResult types. N4 color map constants: N1=--color-info-500, N2=--color-success-500, N3=--color-warning-500, N4=--color-accent-500
- [x] 3.2 Create `frontend/src/features/teacher/trace/store.ts` with `useTraceStore` — session, events, metrics, verification, snapshots, chatMessages, isLoading, error, fetchTrace(sessionId)

## 4. Frontend — Trace Page Components

- [x] 4.1 Create `EventTimeline.tsx` — vertical timeline with N4 color-coded nodes, event type Spanish labels, timestamps, payload summaries
- [x] 4.2 Create `CodeEvolutionPanel.tsx` — scrollable list of snapshots with inline diff view (additions green, deletions red). Use simple line-by-line diff, no external lib
- [x] 4.3 Create `ChatPanel.tsx` — conversation view reusing ChatMessage styling, fetches tutor messages for the exercise
- [x] 4.4 Create `MetricsSummaryCard.tsx` — compact card with N1-N4 scores, Qe, dependency, risk badge. Shows "Metricas pendientes" if null
- [x] 4.5 Create `IntegrityIndicator.tsx` — green checkmark "Cadena integra" or red alert "Cadena comprometida en evento #N"
- [x] 4.6 Create `TracePage.tsx` — full page layout: header + metrics card + integrity indicator + 3-column layout (timeline | code | chat). Route: `/teacher/trace/:sessionId`

## 5. Frontend — Exercise Patterns

- [x] 5.1 Create `frontend/src/features/teacher/patterns/types.ts` and `store.ts` — sessions for exercise, aggregate metrics
- [x] 5.2 Create `StrategyDistribution.tsx` — bar chart of N2 score ranges (0-25, 25-50, 50-75, 75-100). Simple HTML bars, no chart library
- [x] 5.3 Create `ErrorPatternsSummary.tsx` — cards: avg code runs, % low success efficiency, risk distribution
- [x] 5.4 Create `ExercisePatternsPage.tsx` — route `/teacher/courses/:courseId/exercises/:exerciseId/patterns`. Session table with link to trace

## 6. Frontend — Governance Reports

- [x] 6.1 Create `frontend/src/features/teacher/governance/types.ts` and `store.ts` — events, prompts, loading states
- [x] 6.2 Create `GovernanceEventsTable.tsx` — paginated table of governance events with event_type filter
- [x] 6.3 Create `PromptHistoryTable.tsx` — table of prompts with active badge, hash truncated
- [x] 6.4 Create `GovernanceReportsPage.tsx` — route `/admin/governance`. Tabs: Eventos / Prompts

## 7. Routing + Integration

- [x] 7.1 Add routes to `App.tsx`: `/teacher/trace/:sessionId`, `/teacher/courses/:courseId/exercises/:exerciseId/patterns`, `/admin/governance`
- [x] 7.2 Add navigation links: session rows in teacher dashboard link to trace, exercise rows link to patterns
- [x] 7.3 Add "Governance" link in AppLayout sidebar for admin role

## 8. Tests

- [x] 8.1 Unit tests for trace endpoint: returns unified data, handles not found, handles open session
- [x] 8.2 Unit tests for timeline endpoint: pagination, n4_level extraction
- [x] 8.3 Unit tests for code-evolution endpoint: joins events with snapshots, empty case
- [x] 8.4 Unit tests for governance prompts endpoint: pagination, admin-only RBAC
- [x] 8.5 Unit tests for sessions list endpoint: commission filter, student filter, pagination
