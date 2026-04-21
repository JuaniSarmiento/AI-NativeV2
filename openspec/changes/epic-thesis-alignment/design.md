## Context

The AI-Native platform implements the N4 cognitive observation model for university programming education. After a thorough audit against the doctoral thesis requirements, 11 blocks of work remain — ranging from hash chain formula corrections to new frontend components. The codebase already has solid foundations: the classifier, event model, and MetricsEngine are well-structured. The gaps are specific and well-scoped.

Key existing state:
- `compute_event_hash()` in `ctr_builder.py` hashes `previous_hash:event_type:json(payload):timestamp` — prompt_hash is inside payload but not explicit
- `CoherenceEngine` in `coherence.py` is pure computation (no DB, no async) — uses Jaccard for code-discourse
- `_compute_qe_composite()` averages 4 N4-derived sub-scores only
- `GuardrailsProcessor` checks 3 rules post-LLM (excessive_code, direct_solution, non_socratic)
- `_create_llm_adapter()` in router.py selects provider but has no fallback
- `TutorSystemPrompt` model has `version` string but no `change_type` or `change_justification`

## Goals / Non-Goals

**Goals:**
- Close all thesis alignment gaps so the implementation matches the doctoral document
- Maintain backward compatibility where possible (especially hash chains)
- Keep changes modular — each block is independently deployable
- Preserve the pure-computation property of CoherenceEngine (move DB queries to callers)

**Non-Goals:**
- Rewriting the existing MetricsEngine or CoherenceEngine architecture
- Building a full anonymization/GDPR compliance framework (minimal pseudonymization only)
- Real-time adversarial detection with ML models (rule-based heuristics are sufficient)
- Implementing new frontend pages (only extending existing dashboard components)
- Changing the hash chain for existing events (versioned verification, not retroactive change)

## Decisions

### D1 — Hash chain versioning (B3)

**Decision**: Introduce `chain_version` field on `CognitiveSession`. Existing sessions keep `chain_version=1` (current formula). New sessions use `chain_version=2` with explicit prompt_hash.

**V2 formula**: `SHA-256(previous_hash + ":" + event_type + ":" + json(payload) + ":" + timestamp_iso + ":" + prompt_hash_or_empty)`

**Why not just change the formula?** Retroactively changing would invalidate all existing hash chains. The thesis requires auditability — breaking existing chains defeats the purpose. Versioned verification checks V1 chains with V1 formula, V2 with V2.

**Alternative considered**: Using a migration to recalculate all existing hashes. Rejected because: (a) computationally expensive, (b) the original hashes were the ones verified at creation time — recalculating changes the audit trail.

**Files**: `ctr_builder.py` (add `prompt_hash` param with default `""`), `cognitive/service.py` (pass prompt_hash when available), `cognitive/models.py` (add `chain_version` to CognitiveSession).

### D2 — LLM-based code-discourse coherence (B4)

**Decision**: Add a new method `_compute_code_discourse_llm()` to `CoherenceEngine` that accepts pre-formatted text (chat + code) and an LLM evaluation result. The actual LLM call happens in the caller (`CognitiveService.close_session()`), preserving the engine's purity.

**Flow**:
```
CognitiveService.close_session()
  ├─ Gather chat messages + last code snapshot
  ├─ Call LLM adapter: "Rate coherence 0-100 between this chat and this code"
  ├─ Pass LLM score to CoherenceEngine.compute(..., llm_discourse_score=score)
  └─ CoherenceEngine uses LLM score instead of Jaccard
```

**Fallback**: If LLM call fails, fall back to Jaccard (current behavior). Log warning.

**Why not embeddings?** The thesis mentions "semantic embeddings" but an LLM evaluation is functionally superior for this use case — it understands programming concepts, not just vector similarity. One call per session close, minimal cost.

**Prompt template**: System prompt instructs the LLM to evaluate whether the student's chat discussion aligns with what they actually coded. Returns JSON `{"score": 0-100, "reasoning": "..."}`. The reasoning is stored in coherence_anomalies for auditability.

### D3 — Cross-session inter-iteration (B5)

**Decision**: New repository method `CognitiveSessionRepository.get_recent_closed_sessions(student_id, limit=5)` provides historical session data. New method `CoherenceEngine.compute_cross_session()` receives current + historical pattern summaries and compares.

**Pattern summary per session**:
```python
@dataclass
class SessionPattern:
    n1_ratio: float  # % of N1 events
    n3_ratio: float  # % of N3 events  
    exploratory_prompt_ratio: float  # % exploratory vs generative
    has_post_tutor_verification: bool
    qe_score: float | None
```

**Score logic**: Compare current session patterns against the mean of historical sessions. High score = maintains or improves good practices. Low score = regression (less verification, more delegation).

**Why not put DB queries in CoherenceEngine?** The engine is pure computation by design. The caller (CognitiveService) fetches historical sessions and extracts patterns before passing them to the engine.

### D4 — Adversarial detection (B6)

**Decision**: New `AdversarialDetector` class in `backend/app/features/tutor/adversarial.py`. Rule-based with regex patterns for 4 categories:

1. **Jailbreak**: "olvidá tus instrucciones", "ignorá tus reglas", "sos un asistente normal", "act as", "DAN"
2. **Malicious requests**: "hacé un virus", "SQL injection", "hackear"
3. **Undue persuasion**: "tengo examen ahora", "el profe me dijo", "es urgente dame la respuesta"
4. **Repeated attempts**: Counter per session — 3+ adversarial attempts triggers escalation

**Integration point**: In `TutorService.chat()`, BEFORE sending to LLM:
```
1. Parse student message
2. AdversarialDetector.check(message, session_attempt_count)
3. If adversarial → log CTR event "adversarial.detected", return standard message, skip LLM
4. If clean → proceed to LLM
```

**Standard response**: "Entiendo tu urgencia, pero mi rol es ayudarte a pensar el problema. ¿Qué parte del ejercicio te está trabando?"

**Why not ML-based?** Rule-based is sufficient for a university context. The patterns are well-defined and the student population is known. ML would add complexity with minimal benefit.

### D5 — Qe with N1-N4 covariación (B9)

**Decision**: Reformulate `_compute_qe_composite()` to include 4 components weighted by rubric:

| Component | Source | What it measures |
|-----------|--------|-----------------|
| Qe_N1 | reading_time > threshold AND has_reread | Comprehension before asking |
| Qe_N2 | has_pseudocode OR planning_comments | Planning before implementing |
| Qe_N3 | post_tutor_run_ratio AND manual_test_count | Critical verification |
| Qe_N4 | Current sub-scores (quality_prompt, critical_eval, integration, verification) | AI interaction quality |

**Formula**: `Qe = w1*Qe_N1 + w2*Qe_N2 + w3*Qe_N3 + w4*Qe_N4` where weights come from rubric YAML.

**Why weighted average?** The thesis defines Qe as a "second-order construct" that emerges from how the 4 levels covary. A weighted average is the simplest covariation model that the rubric can tune. More complex models (factor analysis) are out of scope for this implementation.

### D6 — Prompt semantic versioning (B7)

**Decision**: Add two columns to `TutorSystemPrompt`:
- `change_type: Mapped[str | None]` — ENUM-like via CheckConstraint: `'major'`, `'minor'`, `'patch'`
- `change_justification: Mapped[str | None]` — free text explaining why

**Validation in service layer** (not DB constraint):
- `major` → version X.0.0 must increment major
- `minor` → version X.Y.0 must increment minor
- `patch` → version X.Y.Z must increment patch

**Why not DB enum?** String with check constraint is more flexible for Alembic migrations and doesn't require a custom PostgreSQL type.

### D7 — Auto snapshots (B11)

**Decision**: Frontend hook `useSubstantialChangeDetector` monitors the editor content:
- Compares current content with last snapshot content
- Triggers `code.snapshot.auto` when: (a) >10 lines changed, or (b) >3 minutes elapsed since last snapshot
- Debounced to avoid rapid-fire events

**Backend**: Add `code.snapshot.auto` to `_EVENT_TYPE_MAPPING` with `n4_level=None` (lifecycle event, not cognitive). Add `code.snapshot.manual` as alias for explicit save/run triggers.

### D8 — LLM fallback (B10)

**Decision**: New `FallbackLLMAdapter` wrapper that takes primary + secondary adapters:

```
FallbackLLMAdapter
  ├─ primary: LLMAdapter (from config)
  ├─ secondary: LLMAdapter (the other provider)
  └─ stream_response(): try primary → catch LLMUnavailableError → try secondary
```

**Where instantiated**: `_create_llm_adapter()` in router.py. If `TUTOR_LLM_FALLBACK=true` (env var, default false), wraps the primary in FallbackLLMAdapter.

**Logging**: When fallback activates, log warning with provider name and error. Record in governance events.

### D9 — Research export (B13)

**Decision**: New router `backend/app/features/cognitive/export_router.py` with single endpoint:

`GET /api/v1/admin/export/cognitive-data`

**Query params**: `commission_id`, `date_from`, `date_to`, `student_id`, `format` (json|csv), `pseudonymize` (bool)

**Pseudonymization** (B8): When `pseudonymize=true`:
- Replace `student_id` with deterministic hash: `SHA-256(student_id + salt)`
- Strip chat message content from payload (replace with `"[REDACTED]"`)
- Strip code content (replace with line count only)
- Set `is_pseudonymized: true` in response metadata

**Role restriction**: `require_role("admin")` dependency.

### D10 — Dashboard coherence semaphores + breakdown (B12)

**Decision**: Two new React components:

1. **`CoherenceSemaphores`**: Three colored dots (green >70, yellow 40-70, red <40) for temporal, code-discourse, inter-iteration. Tooltip shows exact score. Gray dot when null.

2. **`ScoreBreakdown`**: Expandable accordion inside student row. Lists per-N conditions with check/cross icons. Data comes from `latest_score_breakdown` already in `StudentSummary`.

**No new API calls needed** — data already returned by the dashboard endpoint.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **B3**: Hash chain versioning adds complexity to verification | `verify_chain()` reads `chain_version` and selects formula. Simple conditional, not a plugin system. |
| **B4**: LLM call on session close adds latency | Fire-and-forget pattern — coherence is computed async after session close response is sent to student. Fallback to Jaccard on timeout. |
| **B4**: LLM coherence score variability | Store reasoning for auditability. Rubric can adjust weight if LLM scores are noisy. |
| **B5**: Cross-session query adds DB load | Indexed query on `(student_id, status, closed_at)`. 5 rows max. Negligible. |
| **B6**: Regex-based adversarial detection has false positives | Conservative patterns. Log but don't block on borderline cases. Teacher can review in governance events. |
| **B9**: Qe formula change affects all future scores | Old scores remain in DB. New formula only applies to new session closes. Dashboard shows whatever is stored. |
| **B10**: Fallback adapter masks provider issues | Governance event logged on every fallback. Alert threshold configurable. |
| **B13**: Export of large datasets is slow | Streaming response with cursor-based pagination. CSV uses Python's csv writer with chunked output. |

## Migration Plan

1. **Alembic migration**: Add `chain_version` to CognitiveSession (default 1), `change_type` + `change_justification` to TutorSystemPrompt
2. **Deploy backend** with new code — all existing functionality continues unchanged
3. **New sessions** automatically use chain_version=2
4. **Frontend deploy** with auto-snapshot hook and dashboard components
5. **Rollback**: Remove migration, revert code. No data loss — new fields are nullable.

## Open Questions

1. **Qe weights**: What should the default weights for N1/N2/N3/N4 contributions be? Thesis should define these. Defaulting to equal weights (0.25 each) until specified.
2. **Adversarial escalation**: How should the teacher be notified? Push notification? Dashboard indicator? Starting with governance event + dashboard flag.
3. **Export salt for pseudonymization**: Should it be configurable per-export or fixed per-deployment? Leaning toward fixed per-deployment via env var.
