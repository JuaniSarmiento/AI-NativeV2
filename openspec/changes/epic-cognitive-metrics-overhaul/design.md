## Context

The cognitive metrics pipeline processes student events through a chain: Frontend/Backend emits → Redis Streams → CognitiveEventConsumer classifies → CognitiveService persists → MetricsEngine computes scores on session close → Dashboard displays.

Current problems:
1. The classifier maps `code.snapshot` as N1 and `submission.created` as N2, inflating scores
2. MetricsEngine uses hardcoded event type sets instead of the classified `n4_level`
3. `n4_level` is buried in JSONB payload with no index
4. Commission AVG aggregates per-session instead of per-student
5. Critical cognitive events from the thesis are not captured
6. Dashboard lacks coherence visibility, score explanations, and evolution tracking
7. Several Qe sub-score calculations have logical bugs

The database will be wiped clean for this release — no backward compatibility or migration of existing data required.

## Goals / Non-Goals

**Goals:**
- Produce accurate N1-N4 scores that reflect genuine cognitive processes as defined by the N4 model
- Capture 6 new event types that provide evidence for comprehension, strategy, validation, and AI appropriation
- Give docentes actionable visibility into student cognitive profiles at both commission and individual level
- Eliminate score inflation that makes metrics meaningless for pedagogical intervention
- Make `n4_level` a first-class queryable field for analytics

**Non-Goals:**
- LLM-based semantic analysis for `pseudocode.written` or `prompt.reformulated` (use heuristics first, LLM later)
- Real-time score updates (scores compute on session close, not live)
- Mobile-specific dashboard layouts (responsive but not mobile-first for teacher views)
- Recalculation of historical data (clean database start)
- Changes to the tutor's behavior or guardrails
- Changes to the hash chain / CTR integrity mechanism

## Decisions

### D1: Add `n4_level` as a real column, not just payload field

**Choice**: Add `INTEGER NULLABLE` column to `cognitive_events` with a GIN index.

**Alternatives considered**:
- Keep in JSONB with a generated column → PostgreSQL supports this but adds complexity to the ORM layer
- Create a materialized view → stale data risk, refresh overhead

**Rationale**: Direct column is simplest, fastest to query, and plays well with SQLAlchemy. The consumer already knows the level at write time, so there's zero cost to populate it.

### D2: MetricsEngine filters by n4_level, not event_type sets

**Choice**: Replace `_N1_EVENT_TYPES` frozensets with `_events_by_level(events, level)` that reads the `n4_level` attribute.

**Rationale**: The classifier is the single source of truth for what level an event belongs to. The MetricsEngine should trust the classification, not re-implement it with a different mapping. This also means new event types automatically flow into the correct N score without MetricsEngine changes.

### D3: Frontend emits reading_time and reread; backend detects pseudocode, test_manual, code_accepted, reformulated

**Choice**: Split event detection responsibility by where the data lives.

| Event | Emitter | Why |
|-------|---------|-----|
| `problem.reading_time` | Frontend | Only frontend knows focus/visibility state |
| `problem.reread` | Frontend | Only frontend knows tab switches |
| `code.accepted_from_tutor` | Frontend (clipboard) + Backend (similarity) | Dual detection for robustness |
| `pseudocode.written` | Backend (on snapshot) | Requires content analysis of code |
| `test.manual_case` | Backend (on code.run) | Requires parsing executed code |
| `prompt.reformulated` | Backend (in tutor service) | Requires comparison with previous message |

### D4: Score breakdown as structured data in the metrics response

**Choice**: Add a `score_breakdown` JSONB field to `CognitiveMetrics` that stores the detailed reasoning for each N score (which conditions were met/unmet).

**Alternatives considered**:
- Compute breakdown on-the-fly at API time → expensive for dashboard with 30 students
- Store only in ReasoningRecord → too verbose, need a summary

**Rationale**: Computing once at session close and storing as JSONB gives fast reads for the dashboard while maintaining full transparency. The frontend renders checkmarks/crosses from this structured data.

### D5: Per-student AVG using DISTINCT ON

**Choice**: Use PostgreSQL `DISTINCT ON (student_id) ORDER BY computed_at DESC` to get the latest session per student, then AVG over those.

**Rationale**: This is the most natural way to express "latest per group" in PostgreSQL, is index-friendly, and produces the semantically correct metric: "how is each student doing NOW".

### D6: Swim lanes as custom SVG component (no library)

**Choice**: Build a custom SVG component for the swim lanes timeline.

**Alternatives considered**:
- Recharts scatter plot → can work but requires heavy customization for 4 fixed lanes
- D3.js → overkill dependency for one chart type
- Canvas → loses interactivity (hover, click)

**Rationale**: The swim lanes have very specific requirements (4 fixed horizontal lanes, time-relative X axis, colored dots, hover tooltip). A custom SVG is ~150 lines, fully controlled, no extra dependency.

### D7: N4 = null shows "Sin interaccion" with semantic meaning

**Choice**: When a student doesn't use the tutor, N4 remains null. The dashboard displays "Sin interaccion" (not "0", not "-"). The risk_level calculation treats N4=null as non-applicable (doesn't contribute to risk from the N4 dimension, but other dimensions still can trigger risk).

**Rationale**: The thesis defines N4 as "interaction with AI". No interaction ≠ bad interaction. It's a valid learning mode. But it shouldn't mask problems in N1-N3 by defaulting to 100.

### D8: Pseudocode detection heuristics

**Choice**: Detect pseudocode in `code.snapshot` using these combined signals:
1. 3+ consecutive comment lines (# or //)
2. Presence of control flow keywords in comments (si, mientras, para, if, while, for, luego, después, primero)
3. Comment-to-code ratio > 0.5 in the snapshot
4. Snapshot appears before first successful `code.run`

Must meet criteria 1 AND (2 OR 3). Criterion 4 is a bonus signal, not required.

### D9: Prompt reformulation detection via TF-IDF cosine similarity

**Choice**: Use TF-IDF vectorization with cosine similarity (threshold 0.4) within a 90-second window. If two consecutive student messages have similarity > 0.4 AND the second is longer or contains more specific terms, emit `prompt.reformulated`.

**Alternatives considered**:
- Jaccard of keywords → too fragile, common words dominate
- LLM classification → too expensive per message, adds latency
- Levenshtein distance → doesn't handle semantic reformulation (same idea, different words)

**Rationale**: TF-IDF cosine is fast (no external API), captures semantic overlap better than character-level metrics, and the 90-second window prevents false positives from unrelated follow-up questions.

## Risks / Trade-offs

**[Risk] Pseudocode detection false positives** → Mitigation: Require 3+ consecutive lines AND control flow keywords. Log detections for manual review in first sprint. Can tune thresholds with real data.

**[Risk] `code.accepted_from_tutor` clipboard detection is evadible** → Mitigation: Backend similarity check as fallback. Student can still type code manually, but this is about measurement accuracy not prevention. Partial detection is better than none.

**[Risk] TF-IDF for reformulation may miss semantic reformulations in different words** → Mitigation: Start with 0.4 threshold (permissive). Can add LLM fallback later for low-confidence cases. The 90-second window already reduces false positive space significantly.

**[Risk] Score breakdown JSONB grows large over time** → Mitigation: Structure is fixed (4 N-scores × ~5 conditions each = ~20 booleans + labels). Under 2KB per session. Not a scaling concern.

**[Risk] Swim lanes SVG performance with many events** → Mitigation: Cap displayed events at 200 per session (aggregate remainder). Typical session has 15-40 events. Not a real concern.

**[Risk] Breaking change in scores makes old documentation/screenshots invalid** → Mitigation: Database wipe means clean start. Document new score semantics in knowledge-base.

**[Trade-off] N4=null doesn't contribute to weighted_total** → This means students who don't use the tutor have their final Qe calculated from fewer dimensions. Acceptable because forcing a score for non-existent behavior would be dishonest.

**[Trade-off] Dual detection for code_accepted adds complexity** → Two detection paths (clipboard + similarity) must be deduplicated. Use a 30-second dedup window: if frontend already emitted for a code block, backend similarity check skips it.
