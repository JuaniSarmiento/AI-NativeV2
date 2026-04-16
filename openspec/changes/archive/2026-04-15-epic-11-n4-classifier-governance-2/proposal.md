## Why

After EPIC-10 (ContextBuilder + GuardrailsProcessor), tutor interactions flow through the backend but the `n4_level` column in `tutor_interactions` was left always NULL. Fase 3 cannot classify cognitive engagement without this signal. Additionally, governance events (policy violations, prompt updates, model changes) had no persistent store.

## What Changes

- New N4Classifier — heuristic classifier for user & assistant messages → N1-N4 + sub-type
- New GovernanceEvent model + migration — persistent store for policy events, prompt lifecycle
- New GovernanceService — records violations, prompt updates, emits to event bus
- New Governance API — paginated, filterable endpoint for admins
- TutorService integration — N4Classifier called post-guardrails, persists n4_level

## Capabilities

### New Capabilities
- `n4-classifier`: Classifies each tutor interaction in N1-N4 with sub-classification critical/exploratory/dependent
- `governance-events-model`: GovernanceEvent SQLAlchemy model in governance schema with Alembic migration
- `governance-service`: Domain service for recording violations, prompt lifecycle, emitting bus events
- `governance-api`: GET /api/v1/governance/events admin-only endpoint

### Modified Capabilities
- `tutor-chat-ws`: Both turns classified, cognitive.classified events emitted, governance events on violations

## Impact

Backend only. New governance module, Alembic migration, modified TutorService. No frontend changes.
