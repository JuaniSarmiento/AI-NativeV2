## 1. GovernanceEvent Model + Migration

- [x] 1.1 Create `app/features/governance/__init__.py` module
- [x] 1.2 Create `app/features/governance/models.py` with GovernanceEvent model
- [x] 1.3 Generate Alembic migration for governance.governance_events table
- [x] 1.4 Register GovernanceEvent model in base metadata imports

## 2. GovernanceService + Repository

- [x] 2.1 Create GovernanceEventRepository with list_events
- [x] 2.2 Create GovernanceService with record_event
- [x] 2.3 Add record_guardrail_violation convenience method
- [x] 2.4 Add record_prompt_lifecycle convenience methods
- [x] 2.5 Add emit_governance_flag method

## 3. Governance API Endpoint

- [x] 3.1 Create governance schemas
- [x] 3.2 Create governance router (admin only, paginated, filterable)
- [x] 3.3 Register governance router in main.py

## 4. N4Classifier Service

- [x] 4.1 Create N4Classifier class
- [x] 4.2 Implement classify_message with N4ClassificationResult
- [x] 4.3 Implement user message heuristics (N1-N4 Spanish patterns)
- [x] 4.4 Implement assistant message heuristics
- [x] 4.5 Implement sub-classification heuristics
- [x] 4.6 Default to N1 when no pattern matches

## 5. Service Integration

- [x] 5.1 Classify user turn, set n4_level
- [x] 5.2 Classify assistant turn, set n4_level
- [x] 5.3 Emit cognitive.classified EventOutbox for each turn
- [x] 5.4 Update ChatResult with n4_level and sub_classification
- [x] 5.5 Wire GovernanceService for guardrail violations

## 6. Outbox Routing Update

- [x] 6.1 Add cognitive prefix routing
- [x] 6.2 Add governance prefix routing

## 7. Tests

- [x] 7.1 Unit tests for N4Classifier (18 tests)
- [x] 7.2 Unit tests for GovernanceService (7 tests)
- [x] 7.3 Unit tests for GovernanceEventRepository
- [x] 7.4 Integration test for governance API endpoint (5 tests)
- [x] 7.5 Integration test for N4 classification flow
