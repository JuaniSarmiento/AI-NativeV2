## Context
EPIC-10 added ContextBuilder + GuardrailsProcessor. n4_level always NULL. governance_events table not yet created.

## Goals / Non-Goals
Goals: N4 classification per interaction, GovernanceEvent model, GovernanceService, admin API, cognitive.classified events.
Non-Goals: LLM classification, governance UI, CTR, aggregated metrics.

## Decisions
- D1: Heuristic regex classifier, priority N4→N3→N2→N1
- D2: VARCHAR(100) event_type, no DB enum
- D3: Direct call from TutorService, not Redis consumer
- D4: N4Classifier after guardrails in chat()
- D5: Governance as separate module
