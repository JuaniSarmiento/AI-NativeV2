## 1. CTR Hash Chain — Prompt Hash (B3)

- [x] 1.1 Add `chain_version` column (Integer, default=1) to `CognitiveSession` model in `backend/app/features/cognitive/models.py`
- [x] 1.2 Create Alembic migration for `chain_version` column on `cognitive_sessions`
- [x] 1.3 Modify `compute_event_hash()` in `ctr_builder.py` to accept optional `prompt_hash` param (default `""`), append to hash string for V2
- [x] 1.4 Modify `verify_chain()` in `ctr_builder.py` to read `chain_version` from session and select formula accordingly
- [x] 1.5 Update `CognitiveService.add_event()` to pass `prompt_hash` when available (from active TutorSystemPrompt)
- [x] 1.6 Set `chain_version=2` on new sessions created by `CognitiveService.open_session()`
- [x] 1.7 Add unit tests for V1 and V2 hash computation and chain verification

## 2. Qe Composite with N1-N4 Covariación (B9)

- [x] 2.1 Add `qe_weights` section to rubric YAML (`backend/rubrics/n4_anexo_b.yaml`) with default weights for N1/N2/N3/N4 (0.25 each)
- [x] 2.2 Update `RubricConfig` dataclass to parse `qe_weights` from YAML
- [x] 2.3 Add `_compute_qe_n1()` method in `MetricsEngine` — score based on reading_time adequacy + problem re-reads
- [x] 2.4 Add `_compute_qe_n2()` method — score based on pseudocode evidence or planning comments
- [x] 2.5 Add `_compute_qe_n3()` method — score based on post-tutor verification runs + manual test cases
- [x] 2.6 Refactor `_compute_qe_composite()` to weighted average of Qe_N1, Qe_N2, Qe_N3, Qe_N4
- [x] 2.7 Add unit tests for Qe composite with various event distributions (all levels, missing levels, only N4)

## 3. LLM-Based Code-Discourse Coherence (B4)

- [x] 3.1 Create coherence evaluation prompt template (system prompt + user message format) in `backend/app/features/evaluation/prompts/`
- [x] 3.2 Add `llm_discourse_score` optional param to `CoherenceEngine.compute()` — when provided, use it instead of Jaccard
- [x] 3.3 In `CognitiveService.close_session()`, call LLM adapter with coherence prompt (chat messages + last code snapshot)
- [x] 3.4 Parse LLM JSON response (`score`, `reasoning`), store reasoning in `coherence_anomalies.details.llm_reasoning`
- [x] 3.5 Add try/except around LLM call — on failure, fall back to Jaccard and log warning
- [x] 3.6 Add unit tests for CoherenceEngine with LLM score provided and with fallback to Jaccard

## 4. Cross-Session Inter-Iteration Coherence (B5)

- [x] 4.1 Add `get_recent_closed_sessions(student_id, limit=5)` method to `CognitiveSessionRepository`
- [x] 4.2 Create `SessionPattern` dataclass in `coherence.py` (n1_ratio, n3_ratio, exploratory_prompt_ratio, has_post_tutor_verification, qe_score)
- [x] 4.3 Add `compute_cross_session()` method to `CoherenceEngine` — receives current + historical SessionPatterns, returns score
- [x] 4.4 In `CognitiveService.close_session()`, fetch historical sessions, extract patterns, pass to engine
- [x] 4.5 Replace current intra-session `inter_iteration_score` with cross-session result when historical data available
- [x] 4.6 Add unit tests — first session (None), 3 prior sessions, 5+ prior sessions, regression detection

## 5. Adversarial Detection (B6)

- [x] 5.1 Create `backend/app/features/tutor/adversarial.py` with `AdversarialDetector` class
- [x] 5.2 Implement regex pattern sets for 4 categories: jailbreak, malicious, persuasion (Spanish + English)
- [x] 5.3 Implement `check(message, session_attempt_count)` method returning detection result with category
- [x] 5.4 Add session-level attempt counter (in-memory dict keyed by session_id, reset on new session)
- [x] 5.5 Integrate in `TutorService.chat()` — call detector before LLM, if adversarial: log CTR event, return standard message, skip LLM
- [x] 5.6 Log `adversarial.detected` event type in CTR with `payload.category` and `payload.attempt_number`
- [x] 5.7 On 3+ attempts per session, log governance event `adversarial.escalation`
- [x] 5.8 Add unit tests — each category detected, false positive avoidance, escalation threshold

## 6. Extended Guardrails GP3/GP5 (B6 cont.)

- [x] 6.1 Add `_check_gp3_code_reference()` method to `GuardrailsProcessor` — checks if response references student's code patterns
- [x] 6.2 Add `_check_gp5_test_suggestion()` method — checks if debugging response suggests concrete test values
- [x] 6.3 Modify `analyze()` to accept optional `student_code` param for GP3 context
- [x] 6.4 GP3 and GP5 violations are audit-only (log event, don't block response)
- [x] 6.5 Add unit tests for GP3 and GP5 detection

## 7. Dashboard — Coherence Semaphores + Score Breakdown (B12)

- [x] 7.1 Create `CoherenceSemaphores` React component — 3 colored dots with tooltip showing exact score
- [x] 7.2 Integrate `CoherenceSemaphores` into `StudentScoresTable` for each student row
- [x] 7.3 Create `ScoreBreakdown` React component — expandable panel with per-N check/cross indicators
- [x] 7.4 Integrate `ScoreBreakdown` as expandable row detail in the dashboard table
- [x] 7.5 Handle null states (gray dot for no data, "Sin desglose disponible" for missing breakdown)
- [x] 7.6 Style semaphores and breakdown with TailwindCSS design tokens (green/yellow/red from theme)

## 8. Semantic Prompt Versioning (B7)

- [x] 8.1 Add `change_type` (String, CheckConstraint in ['major','minor','patch'], nullable) and `change_justification` (Text, nullable) to `TutorSystemPrompt` model
- [x] 8.2 Create Alembic migration for the 2 new columns
- [x] 8.3 Add version validation logic in governance service — parse semver, validate change_type matches version increment
- [x] 8.4 Update prompt creation endpoint to accept and validate `change_type` + `change_justification`
- [x] 8.5 Add unit tests for version validation (major/minor/patch matches, mismatches rejected)

## 9. Auto Snapshots (B11)

- [x] 9.1 Create `useSubstantialChangeDetector` hook in frontend — monitors editor content, detects >10 lines changed or >3 min elapsed
- [x] 9.2 Emit `code.snapshot.auto` event via existing WebSocket/REST when threshold is met
- [x] 9.3 Add `code.snapshot.auto` to `_EVENT_TYPE_MAPPING` in `classifier.py` with `n4_level=None`
- [x] 9.4 Debounce detection to avoid rapid-fire events (min 30s between auto snapshots)
- [x] 9.5 Add unit test for classifier mapping of `code.snapshot.auto`

## 10. LLM Fallback (B10)

- [x] 10.1 Create `FallbackLLMAdapter` class in `llm_adapter.py` wrapping primary + secondary adapters
- [x] 10.2 Implement `stream_response()` with try/except on `LLMUnavailableError` for primary, retry with secondary
- [x] 10.3 Add `TUTOR_LLM_FALLBACK` env var to settings (default false)
- [x] 10.4 Update `_create_llm_adapter()` in `router.py` to wrap with FallbackLLMAdapter when enabled
- [x] 10.5 Log governance event on fallback activation
- [x] 10.6 Add unit tests — primary success (no fallback), primary fail + secondary success, both fail

## 11. Pseudonymization (B8)

- [x] 11.1 Create `backend/app/features/cognitive/pseudonymize.py` with `scrub_payload()` utility function
- [x] 11.2 Implement field-level redaction: `message_content` → `[REDACTED]`, `code` → `{"line_count": N}`
- [x] 11.3 Implement `pseudonymize_student_id(student_id, salt)` using SHA-256
- [x] 11.4 Add `PSEUDONYMIZATION_SALT` env var to settings
- [x] 11.5 Add docstring to `CognitiveEvent.student_id` documenting UUID as pseudonym
- [x] 11.6 Add unit tests for payload scrubbing and ID pseudonymization

## 12. Research Export Endpoint (B13)

- [x] 12.1 Create `backend/app/features/cognitive/export_router.py` with `GET /api/v1/admin/export/cognitive-data`
- [x] 12.2 Implement query params: `commission_id`, `date_from`, `date_to`, `student_id`, `format` (json|csv), `pseudonymize` (bool)
- [x] 12.3 Create export service method that fetches sessions + metrics + events with filters
- [x] 12.4 Implement JSON response format with streaming for large datasets
- [x] 12.5 Implement CSV response format using Python csv writer with chunked StreamingResponse
- [x] 12.6 Apply `require_role("admin")` dependency to endpoint
- [x] 12.7 Integrate pseudonymize.py when `pseudonymize=true` — scrub payloads, hash student IDs
- [x] 12.8 Add `is_pseudonymized` field to response metadata
- [x] 12.9 Add integration tests — JSON export, CSV export, filtered, pseudonymized, role-restricted
