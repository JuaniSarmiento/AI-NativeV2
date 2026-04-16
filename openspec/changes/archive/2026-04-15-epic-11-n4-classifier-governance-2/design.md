## Context

EPIC-10 added ContextBuilder and GuardrailsProcessor. The n4_level field exists since EPIC-09 but always NULL. governance_events table defined in KB but has no model or migration. N4Classifier operates at individual INTERACTION level (Fase 2), distinct from Fase 3 session classifier.

## Goals / Non-Goals

**Goals:** Classify each interaction N1-N4, sub-classify, persist n4_level, GovernanceEvent model, GovernanceService, admin API, cognitive.classified events

**Non-Goals:** LLM classification (v2), governance UI (EPIC-16), CTR/hash chain (EPIC-13), aggregated metrics (EPIC-14)

## Decisions

- D1: Heuristic regex classifier, separate user/assistant patterns, priority N4→N3→N2→N1
- D2: GovernanceEvent VARCHAR(100) event_type, no DB enum, JSONB details
- D3: GovernanceService direct call from TutorService, not separate Redis consumer
- D4: N4Classifier after guardrails check in TutorService.chat()
- D5: Governance as separate module app/features/governance/

## Risks / Trade-offs

- Heuristic precision limited → pluggable for LLM v2
- <1ms overhead per interaction
- governance_events unbounded → partition by created_at in production
