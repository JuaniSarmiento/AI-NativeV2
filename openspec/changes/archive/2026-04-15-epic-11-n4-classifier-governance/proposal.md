## Why

n4_level in tutor_interactions always NULL — Fase 3 blocked. Governance events had no persistent store.

## What Changes

- N4Classifier (heuristic, N1-N4 + sub-classification)
- GovernanceEvent model + Alembic migration
- GovernanceService (violations, prompt lifecycle, bus events)
- Governance API (admin GET endpoint)
- TutorService integration (classify both turns, persist, emit)

## Capabilities

### New
- n4-classifier, governance-events-model, governance-service, governance-api

### Modified
- tutor-chat-ws (N4 classification integrated)

## Impact

Backend only. New governance module + migration. No frontend.
