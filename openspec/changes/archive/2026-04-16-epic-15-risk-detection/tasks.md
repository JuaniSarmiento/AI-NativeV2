## 1. Model + Migration

- [x] 1.1 Create `app/features/risk/__init__.py` and `app/features/risk/models.py` with `RiskAssessment` model in schema `analytics` (id, student_id, commission_id, risk_level String(20), risk_factors JSONB, recommendation TEXT nullable, triggered_by String(20), assessed_at, acknowledged_by nullable, acknowledged_at nullable). Indexes on student_id, commission_id, risk_level. UniqueConstraint on (student_id, commission_id, func.date(assessed_at))
- [x] 1.2 Create Alembic migration `014_add_risk_assessments.py` that creates `analytics.risk_assessments` with all columns, indexes, and unique constraint. Include downgrade
- [x] 1.3 Register `RiskAssessment` in `app/shared/models/__init__.py` so Alembic sees it

## 2. Repository

- [x] 2.1 Create `app/features/risk/repositories.py` with `RiskAssessmentRepository(BaseRepository[RiskAssessment])`. Methods: `get_by_commission(commission_id, page, per_page, risk_level_filter)`, `get_by_student(student_id, page, per_page, commission_id_filter)`, `get_active_by_student_commission(student_id, commission_id)`, `upsert_daily(data_dict)` using insert-on-conflict-update on the unique constraint

## 3. Risk Worker Service

- [x] 3.1 Create `app/features/risk/service.py` with `RiskWorker` class. Constructor receives `CognitiveMetricsRepository`, `RiskAssessmentRepository`, and `AsyncSession` (for CognitiveSession queries). Pure domain service, no FastAPI imports
- [x] 3.2 Implement `_detect_dependency_factor(metrics_list)` — average dependency_score across last 5 sessions, threshold 0.5. Returns factor dict or None
- [x] 3.3 Implement `_detect_disengagement_factor(sessions, commission_id)` — count sessions in last 7 days, expected minimum 2. Returns factor dict or None
- [x] 3.4 Implement `_detect_stagnation_factor(metrics_list)` — compute score trend across last 3 sessions via simple linear slope. Returns factor dict or None
- [x] 3.5 Implement `_compute_risk_level(factors)` — critical if any score >= 0.8 or 2+ factors >= 0.6, high if any >= 0.6, medium if any >= 0.4, low otherwise
- [x] 3.6 Implement `_generate_recommendation(factors)` — Spanish text, 1-3 sentences, actionable for docente
- [x] 3.7 Implement `assess_student(student_id, commission_id, triggered_by)` — orchestrates factor detection, risk level, recommendation, upsert via repository
- [x] 3.8 Implement `assess_commission(commission_id, triggered_by)` — queries enrolled students from CognitiveSession (denormalized commission_id), calls assess_student for each. Returns count

## 4. Schemas

- [x] 4.1 Create `app/features/risk/schemas.py` with `RiskAssessmentResponse` (Pydantic v2, from_attributes=True), `RiskAssessmentListResponse` (standard envelope with pagination meta), `AssessCommissionResponse` (assessed_count int)

## 5. Router

- [x] 5.1 Create `app/features/risk/router.py` with 4 endpoints: GET commissions/{id}/risks, GET students/{id}/risks, PATCH risks/{id}/acknowledge, POST commissions/{id}/risks/assess. All require docente/admin role
- [x] 5.2 Register risk router in `app/main.py` `_register_routers()`

## 6. Frontend — Store + Types

- [x] 6.1 Add risk types to `frontend/src/features/teacher/dashboard/types.ts`: `RiskAssessment` interface, `RISK_FACTOR_LABELS` map (dependency → Dependencia, disengagement → Desvinculacion, stagnation → Estancamiento)
- [x] 6.2 Extend `useTeacherDashboardStore` in `store.ts` with: `risks`, `isLoadingRisks`, `fetchRisks(commissionId)`, `acknowledgeRisk(riskId)`, `triggerAssessment(commissionId)` actions

## 7. Frontend — Components

- [x] 7.1 Create `RiskAlertsTable.tsx` component — table of risk alerts with color-coded risk_level, expanded risk_factors, recommendation, assessed_at, and Acknowledge button. Minimalist UI with project design tokens
- [x] 7.2 Create `RiskBadge.tsx` component — small inline badge with risk level color and Spanish label, for use in StudentScoresTable rows
- [x] 7.3 Modify `StudentScoresTable.tsx` to show RiskBadge next to student name based on risk data from the store
- [x] 7.4 Modify `TeacherDashboard.tsx` to include RiskAlertsTable section and an "Evaluar Riesgo" button that triggers manual assessment

## 8. Tests

- [x] 8.1 Unit tests for RiskWorker: dependency factor detection (above/below threshold), disengagement detection, stagnation detection, risk level computation, recommendation generation, idempotency
- [x] 8.2 Unit tests for RiskAssessmentRepository: get_by_commission pagination, get_by_student with filter, upsert_daily idempotency
- [x] 8.3 Unit tests for risk router: list by commission, student history, acknowledge flow, manual trigger, RBAC (alumno denied)
