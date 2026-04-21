## Why

The AI-Native platform implements the N4 cognitive observation model but has critical gaps between its current implementation and the doctoral thesis requirements. Several constructs are incomplete (Qe only uses N4, coherence is keyword-based instead of semantic, inter-iteration is intra-session only), security features are missing (adversarial detection, pseudonymization), governance is partial (no semantic prompt versioning), and research tooling doesn't exist (no data export). These gaps must be closed before the thesis defense.

## What Changes

### Backend — Cognitive & Evaluation Engine
- **Explicit prompt_hash in CTR hash chain**: Add `prompt_hash` as a dedicated parameter in `compute_event_hash()` formula, not just embedded in payload. **BREAKING**: invalidates existing hash chains — requires migration strategy.
- **LLM-based code-discourse coherence**: Replace Jaccard keyword overlap in `CoherenceEngine._compute_code_discourse_coherence()` with a single LLM call per session close.
- **Cross-session inter-iteration coherence**: New `compute_cross_session_coherence()` that compares patterns across the student's last 5 sessions instead of only within the current session.
- **Qe composite with N1-N4 covariación**: Reformulate `_compute_qe_composite()` to include contributions from all 4 cognitive levels, not just N4-derived sub-scores.

### Backend — Tutor Security & Governance
- **Adversarial/jailbreak detection**: New `adversarial.py` module detecting 4 types of adversarial behavior (jailbreak, malicious requests, undue persuasion, repeated attempts). Integrated pre-LLM in `TutorService.chat()`.
- **Extended guardrails GP3/GP5**: Add verification that tutor references student's actual code (GP3) and suggests concrete test cases (GP5).
- **Semantic prompt versioning**: Add `change_justification` and `change_type` (major/minor/patch) fields to `TutorSystemPrompt` model with validation rules.

### Backend — Research & Compliance
- **Pseudonymization layer**: Document UUIDs as pseudonyms, add payload scrubbing for exports, `is_pseudonymized` flag.
- **Research export endpoint**: `GET /api/v1/admin/export/cognitive-data` with CSV/JSON, filters, role-restricted access.

### Frontend — Code Capture & Dashboard
- **Substantial-change auto snapshots**: Detect >10 lines changed or >3 minutes elapsed in editor, emit `code.snapshot.auto` as distinct event type.
- **Coherence semaphores on dashboard**: Three traffic-light indicators for temporal, code-discourse, and inter-iteration coherence scores.
- **Score breakdown detail UI**: Expandable per-student panel showing per-N event contributions with check/cross indicators.

### Backend — LLM Resilience
- **Automatic LLM fallback**: Adapter factory with try/catch fallback from primary to secondary provider on `LLMUnavailableError`.

## Capabilities

### New Capabilities
- `adversarial-detection`: Jailbreak and adversarial behavior detection for the tutor, integrated pre-LLM with CTR event logging
- `research-export`: Admin/researcher endpoint for structured cognitive data export with pseudonymization support
- `pseudonymization`: Payload scrubbing and pseudonymization layer for research compliance
- `auto-snapshots`: Frontend substantial-change detection emitting differentiated `code.snapshot.auto` events
- `llm-fallback`: Automatic provider failover in the LLM adapter layer

### Modified Capabilities
- `cognitive-trace-api`: Explicit `prompt_hash` as dedicated hash chain input (not just payload field)
- `evaluation-engine`: LLM-based code-discourse coherence, cross-session inter-iteration, Qe with N1-N4 covariación
- `tutor-guardrails`: Add GP3 (reference student's code) and GP5 (suggest concrete test) verifications
- `governance-prompts-api`: Semantic versioning fields (`change_justification`, `change_type`) on TutorSystemPrompt
- `tutor-llm-adapter`: Fallback mechanism on provider failure
- `teacher-dashboard-frontend`: Coherence semaphores and score breakdown detail UI

## Impact

- **Database**: 1 new migration (prompt versioning fields), potential hash chain migration for B3
- **Models**: `TutorSystemPrompt` (2 new fields), new `AdversarialAttempt` tracking
- **APIs**: 1 new endpoint (export), modified prompt creation endpoint (validation)
- **Frontend**: 3 new components (semaphores, breakdown, auto-snapshot hook), 1 modified (dashboard table)
- **Dependencies**: LLM adapter used by coherence engine (new dependency path)
- **Performance**: 1 additional LLM call per session close (coherence), 1 additional query per session close (cross-session)
- **Breaking**: Hash chain formula change invalidates existing chains — needs versioned verification
