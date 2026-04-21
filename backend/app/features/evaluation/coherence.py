"""CoherenceEngine — pure computation module for EPIC-20 Fase C.

IMPORTANT: This module has ZERO database I/O and ZERO FastAPI imports.
It is pure Python domain logic that can be unit-tested without any
infrastructure dependencies.

Three coherence dimensions are measured:
  1. Temporal coherence — N-level event sequence is logically ordered.
  2. Code-discourse coherence — chat keywords overlap with code changes.
  3. Inter-iteration consistency — no unexplained large code jumps.

All score values use Decimal arithmetic to match the NUMERIC(5,2) columns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.features.evaluation.rubric import RubricConfig
from app.features.evaluation.service import _clamp, _d2

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop-word list for keyword extraction
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    {
        "the", "and", "for", "that", "with", "this", "from", "have",
        "will", "your", "what", "when", "then", "they", "some", "into",
        "been", "also", "more", "such", "than", "like", "very", "just",
        "can", "not", "are", "was", "were", "its", "our", "out", "but",
        "all", "one", "you", "how", "may", "has", "had", "her", "his",
        "him", "she", "who", "use", "used", "using", "about", "would",
        "could", "should", "must", "each", "both", "here", "there",
        "any", "only", "over", "same", "other", "after", "print",
        "true", "false", "none", "pass", "self", "return", "def",
        "class", "import", "from",
    }
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class CoherenceResult:
    """All coherence fields that map 1:1 onto the new CognitiveMetrics columns."""

    temporal_coherence_score: Decimal | None
    code_discourse_score: Decimal | None
    inter_iteration_score: Decimal | None
    coherence_anomalies: dict  # type: ignore[type-arg]  # {"anomalies": [...], "details": {...}}
    prompt_type_distribution: dict  # type: ignore[type-arg]  # {"exploratory": N, "verifier": N, "generative": N}


@dataclass
class SessionPattern:
    """Extracted behavioural pattern from a single closed session (B5).

    Used by compute_cross_session() to compare current vs historical sessions.
    All ratio fields are in [0.0, 1.0] (not 0-100 percentages).
    """

    n1_ratio: float
    """Fraction of events that are N1-level (reading/comprehension)."""

    n3_ratio: float
    """Fraction of events that are N3-level (validation/testing)."""

    exploratory_prompt_ratio: float
    """Fraction of tutor.question_asked with prompt_type == "exploratory"."""

    has_post_tutor_verification: bool
    """True when at least one code.run follows a tutor.response_received."""

    qe_score: float | None
    """Qe composite score from CognitiveMetrics (0-100), or None if not computed."""


# ---------------------------------------------------------------------------
# CoherenceEngine
# ---------------------------------------------------------------------------


class CoherenceEngine:
    """Pure computation engine for the three coherence dimensions.

    No async, no DB, no FastAPI — only deterministic computation over
    the lists of events, chat messages, and code snapshots provided by
    the caller (CognitiveService.close_session).

    Usage:
        engine = CoherenceEngine(load_rubric())
        result = engine.compute(events, chat_messages, code_snapshots)
    """

    def __init__(self, rubric: RubricConfig) -> None:
        self._rubric = rubric

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(
        self,
        events: list[Any],
        chat_messages: list[Any],
        code_snapshots: list[dict[str, Any]],
        llm_discourse_score: Decimal | None = None,
    ) -> CoherenceResult:
        """Compute all coherence scores.

        Args:
            events: CognitiveEvent ORM instances ordered by sequence_number ASC.
            chat_messages: TutorInteraction ORM instances for the session.
            code_snapshots: Dicts produced by CognitiveService.get_code_evolution()
                            — each dict has at least "code", "snapshot_at",
                            "diff_unified" (str | None).
            llm_discourse_score: When provided (not None), this LLM-generated score
                                 is used directly as code_discourse_score instead of
                                 computing the Jaccard-based estimate. (B4)

        Returns:
            CoherenceResult with the five fields ready for persistence.
        """
        prompt_type_distribution = self._compute_prompt_type_distribution(events)
        temporal_coherence_score, temporal_anomalies = self._compute_temporal_coherence(
            events, prompt_type_distribution
        )
        if llm_discourse_score is not None:
            code_discourse_score: Decimal | None = _clamp(_d2(llm_discourse_score))
        else:
            code_discourse_score = self._compute_code_discourse_coherence(
                chat_messages, code_snapshots
            )
        inter_iteration_score, iteration_anomalies = self._compute_inter_iteration_consistency(
            code_snapshots
        )

        # Merge anomaly lists and details
        all_anomaly_names: list[str] = temporal_anomalies["anomalies"] + iteration_anomalies["anomalies"]
        merged_details: dict[str, Any] = {
            **temporal_anomalies["details"],
            **iteration_anomalies["details"],
        }
        coherence_anomalies: dict[str, Any] = {
            "anomalies": all_anomaly_names,
            "details": merged_details,
        }

        logger.debug(
            "Coherence computed",
            extra={
                "temporal": str(temporal_coherence_score),
                "code_discourse": str(code_discourse_score),
                "inter_iteration": str(inter_iteration_score),
                "anomalies": all_anomaly_names,
            },
        )

        return CoherenceResult(
            temporal_coherence_score=temporal_coherence_score,
            code_discourse_score=code_discourse_score,
            inter_iteration_score=inter_iteration_score,
            coherence_anomalies=coherence_anomalies,
            prompt_type_distribution=prompt_type_distribution,
        )

    # ------------------------------------------------------------------
    # B5 — Cross-session inter-iteration coherence
    # ------------------------------------------------------------------

    def compute_cross_session(
        self,
        current: SessionPattern,
        historical: list[SessionPattern],
    ) -> Decimal | None:
        """Score the student's learning trajectory across multiple sessions.

        Compares the current session's behavioural pattern against the mean
        of historical sessions on four dimensions. The score reflects whether
        the student is maintaining or improving their cognitive engagement.

        Scoring (base 50, adjusted up/down by dimension comparisons):
          - n1_ratio maintained or improved → +25
          - n3_ratio maintained or improved → +25
          - exploratory_prompt_ratio maintained or improved → +25
          - has_post_tutor_verification when historical had it → +25

        When all four dimensions improve: 100.
        When all four regress: 0 (base 50 - 4*12.5, but floors at 0).

        Returns None if historical list is empty.

        Args:
            current:    Pattern extracted from the session being closed.
            historical: Patterns from up to 5 prior closed sessions.
        """
        if not historical:
            return None

        # Compute per-dimension means from historical sessions
        mean_n1 = sum(p.n1_ratio for p in historical) / len(historical)
        mean_n3 = sum(p.n3_ratio for p in historical) / len(historical)
        mean_exploratory = sum(p.exploratory_prompt_ratio for p in historical) / len(historical)
        hist_has_verification = any(p.has_post_tutor_verification for p in historical)

        score = 50.0
        _EPS = 1e-9  # float arithmetic tolerance

        # Each dimension contributes ±12.5 relative to the base
        if current.n1_ratio >= mean_n1 - _EPS:
            score += 12.5
        else:
            score -= 12.5

        if current.n3_ratio >= mean_n3 - _EPS:
            score += 12.5
        else:
            score -= 12.5

        if current.exploratory_prompt_ratio >= mean_exploratory - _EPS:
            score += 12.5
        else:
            score -= 12.5

        if hist_has_verification and current.has_post_tutor_verification:
            score += 12.5
        elif hist_has_verification and not current.has_post_tutor_verification:
            score -= 12.5
        else:
            # Historical had no verification habit — no bonus/penalty
            pass

        return _clamp(_d2(score))

    # ------------------------------------------------------------------
    # Task 3.8 — Prompt type distribution
    # ------------------------------------------------------------------

    def _compute_prompt_type_distribution(
        self, events: list[Any]
    ) -> dict[str, int]:
        """Count prompt types from tutor.question_asked events.

        Returns:
            {"exploratory": N, "verifier": N, "generative": N}
        """
        distribution: dict[str, int] = {"exploratory": 0, "verifier": 0, "generative": 0}
        for event in events:
            if event.event_type != "tutor.question_asked":
                continue
            payload = event.payload if isinstance(event.payload, dict) else {}
            prompt_type = payload.get("prompt_type", "exploratory")
            if prompt_type in distribution:
                distribution[prompt_type] += 1
            else:
                # Unknown prompt type — count as exploratory to avoid silent data loss
                distribution["exploratory"] += 1
        return distribution

    # ------------------------------------------------------------------
    # Task 3.4 — Temporal coherence
    # ------------------------------------------------------------------

    def _compute_temporal_coherence(
        self,
        events: list[Any],
        prompt_type_distribution: dict[str, int],
    ) -> tuple[Decimal | None, dict[str, Any]]:
        """Analyse the N-level sequence from events.

        Anomalies detected:
          - solution_without_comprehension: submission.created before any reads_problem
          - pure_delegation: >60% of tutor questions are "generative"
          - n4_without_n1: N4-level events exist but no N1 events

        Score: start at 100, subtract 25 per anomaly, clamp to 0-100.

        Returns:
            (score_or_None, anomaly_dict)
        """
        if not events:
            return None, {"anomalies": [], "details": {}}

        anomalies: list[str] = []
        details: dict[str, Any] = {}

        event_types = [e.event_type for e in events]

        # Anomaly 1: solution_without_comprehension
        has_reads_problem = any(et == "reads_problem" for et in event_types)
        first_submission_idx: int | None = next(
            (i for i, et in enumerate(event_types) if et == "submission.created"),
            None,
        )
        if first_submission_idx is not None and not has_reads_problem:
            anomalies.append("solution_without_comprehension")
            details["solution_without_comprehension"] = {
                "first_submission_sequence": first_submission_idx + 1,
                "reads_problem_found": False,
            }

        # Anomaly 2: pure_delegation
        total_tutor_questions = sum(prompt_type_distribution.values())
        generative_count = prompt_type_distribution.get("generative", 0)
        threshold = self._rubric.coherence.generative_dominance_threshold
        if total_tutor_questions > 0:
            generative_ratio = generative_count / total_tutor_questions
            if generative_ratio > threshold:
                anomalies.append("pure_delegation")
                details["pure_delegation"] = {
                    "generative_ratio": round(generative_ratio, 3),
                    "threshold": threshold,
                    "generative_count": generative_count,
                    "total_questions": total_tutor_questions,
                }

        # Anomaly 3: n4_without_n1
        has_n4_events = any(
            e.event_type == "tutor.question_asked"
            and isinstance(e.payload, dict)
            and int(e.payload.get("n4_level", 0) or 0) == 4
            for e in events
        )
        has_n1_events = has_reads_problem
        if has_n4_events and not has_n1_events:
            anomalies.append("n4_without_n1")
            details["n4_without_n1"] = {
                "n4_events_found": True,
                "n1_events_found": False,
            }

        score = _clamp(_d2(100 - 25 * len(anomalies)))
        return score, {"anomalies": anomalies, "details": details}

    # ------------------------------------------------------------------
    # Task 3.5 — Code-discourse coherence
    # ------------------------------------------------------------------

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful words from a text string.

        Rules:
          - lowercase, split on non-alpha characters
          - minimum length 4
          - exclude stop words
        """
        import re
        words = re.split(r"[^a-zA-Z]+", text.lower())
        return {w for w in words if len(w) >= 4 and w not in _STOP_WORDS}

    def _compute_code_discourse_coherence(
        self,
        chat_messages: list[Any],
        code_snapshots: list[dict[str, Any]],
    ) -> Decimal | None:
        """Cross-reference chat keywords with code diffs.

        Score = overlap_ratio * 100 where
          overlap_ratio = |intersection| / |union|

        Returns None if there are no chat messages or no code diffs.
        """
        if not chat_messages or not code_snapshots:
            return None

        # Gather chat text — use the `content` field of each TutorInteraction
        chat_text_parts: list[str] = []
        for msg in chat_messages:
            content = getattr(msg, "content", None) or ""
            if content:
                chat_text_parts.append(content)

        if not chat_text_parts:
            return None

        # Gather diff text from snapshots (skip entries with no diff)
        diff_text_parts: list[str] = []
        for entry in code_snapshots:
            diff = entry.get("diff_unified") or ""
            if diff:
                diff_text_parts.append(diff)

        if not diff_text_parts:
            return None

        chat_keywords = self._extract_keywords(" ".join(chat_text_parts))
        diff_keywords = self._extract_keywords(" ".join(diff_text_parts))

        if not chat_keywords or not diff_keywords:
            return None

        intersection = chat_keywords & diff_keywords
        union = chat_keywords | diff_keywords

        if not union:
            return None

        overlap_ratio = len(intersection) / len(union)
        return _clamp(_d2(overlap_ratio * 100))

    # ------------------------------------------------------------------
    # Task 3.6 — Inter-iteration consistency
    # ------------------------------------------------------------------

    def _compute_inter_iteration_consistency(
        self,
        code_snapshots: list[dict[str, Any]],
    ) -> tuple[Decimal | None, dict[str, Any]]:
        """Analyse code snapshot diffs for large unexplained jumps.

        Anomaly: uncritical_integration — any single diff exceeds the
        threshold from rubric (default 50 lines).

        Score: start at 100, subtract 30 per uncritical_integration,
        clamp to 0-100.

        Returns:
            (score_or_None, anomaly_dict)
        """
        # Filter snapshots that have a diff (first snapshot has no diff)
        diffs = [
            entry for entry in code_snapshots if entry.get("diff_unified") is not None
        ]

        if not diffs:
            return None, {"anomalies": [], "details": {}}

        threshold = self._rubric.coherence.external_integration_threshold_lines
        anomalies: list[str] = []
        details: dict[str, Any] = {"uncritical_integration_occurrences": []}

        for entry in diffs:
            diff_text: str = entry["diff_unified"] or ""
            # Count changed lines (lines starting with + or - excluding the --- / +++ headers)
            changed_lines = sum(
                1
                for line in diff_text.splitlines()
                if line.startswith(("+", "-"))
                and not line.startswith(("+++", "---"))
            )
            if changed_lines > threshold:
                details["uncritical_integration_occurrences"].append(
                    {
                        "snapshot_id": entry.get("snapshot_id"),
                        "changed_lines": changed_lines,
                        "threshold": threshold,
                    }
                )

        if details["uncritical_integration_occurrences"]:
            anomalies.append("uncritical_integration")
            details["uncritical_integration_count"] = len(
                details["uncritical_integration_occurrences"]
            )

        # Subtract 30 per occurrence (not per anomaly name — each jump is penalised)
        occurrence_count = len(details["uncritical_integration_occurrences"])
        score = _clamp(_d2(100 - 30 * occurrence_count))
        return score, {"anomalies": anomalies, "details": details}
