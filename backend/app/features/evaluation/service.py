"""MetricsEngine — pure computation service for N1-N4 cognitive metrics.

IMPORTANT: This module has ZERO database I/O and ZERO FastAPI imports.
It is pure Python domain logic that can be unit-tested without any
infrastructure dependencies.

All score values use Decimal arithmetic to preserve exactness when
stored in NUMERIC(5,2) / NUMERIC(4,3) PostgreSQL columns.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.features.evaluation.rubric import RubricConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N1_EVENT_TYPES = frozenset({"reads_problem", "code.snapshot"})
_N2_EVENT_TYPES = frozenset({"submission.created"})
_N3_EVENT_TYPES = frozenset({"code.run"})
_N4_EVENT_TYPES = frozenset({"tutor.question_asked"})
_TUTOR_RESPONSE_TYPES = frozenset({"tutor.response_received"})

_TWO = Decimal("1E-2")   # quantize target for Numeric(5,2)
_THREE = Decimal("1E-3")  # quantize target for Numeric(4,3)


def _d2(value: float | int | Decimal) -> Decimal:
    """Round to 2 decimal places."""
    return Decimal(str(value)).quantize(_TWO, rounding=ROUND_HALF_UP)


def _d3(value: float | int | Decimal) -> Decimal:
    """Round to 3 decimal places."""
    return Decimal(str(value)).quantize(_THREE, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, lo: Decimal = Decimal("0"), hi: Decimal = Decimal("100")) -> Decimal:
    """Clamp a score to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class MetricsDict:
    """All fields that map 1:1 onto CognitiveMetrics columns."""

    n1_comprehension_score: Decimal | None
    n2_strategy_score: Decimal | None
    n3_validation_score: Decimal | None
    n4_ai_interaction_score: Decimal | None
    total_interactions: int
    help_seeking_ratio: Decimal | None
    autonomy_index: Decimal | None
    qe_score: Decimal | None
    qe_quality_prompt: Decimal | None
    qe_critical_evaluation: Decimal | None
    qe_integration: Decimal | None
    qe_verification: Decimal | None
    dependency_score: Decimal | None
    reflection_score: Decimal | None
    success_efficiency: Decimal | None
    risk_level: str | None
    computed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "n1_comprehension_score": self.n1_comprehension_score,
            "n2_strategy_score": self.n2_strategy_score,
            "n3_validation_score": self.n3_validation_score,
            "n4_ai_interaction_score": self.n4_ai_interaction_score,
            "total_interactions": self.total_interactions,
            "help_seeking_ratio": self.help_seeking_ratio,
            "autonomy_index": self.autonomy_index,
            "qe_score": self.qe_score,
            "qe_quality_prompt": self.qe_quality_prompt,
            "qe_critical_evaluation": self.qe_critical_evaluation,
            "qe_integration": self.qe_integration,
            "qe_verification": self.qe_verification,
            "dependency_score": self.dependency_score,
            "reflection_score": self.reflection_score,
            "success_efficiency": self.success_efficiency,
            "risk_level": self.risk_level,
            "computed_at": self.computed_at,
        }


@dataclass
class ComputeResult:
    """Full result of MetricsEngine.compute()."""

    metrics: MetricsDict
    evaluation_profile: dict[str, Any]  # stored in n4_final_score JSONB
    reasoning_details: dict[str, Any]   # stored in ReasoningRecord.details


# ---------------------------------------------------------------------------
# MetricsEngine
# ---------------------------------------------------------------------------


class MetricsEngine:
    """Pure computation engine for N1-N4 cognitive metrics.

    No async, no DB, no FastAPI — only deterministic computation over
    a list of CognitiveEvent objects. This makes it trivially unit-testable.

    Usage:
        engine = MetricsEngine(load_rubric())
        result = engine.compute(session, events)
    """

    def __init__(self, rubric: RubricConfig) -> None:
        self._rubric = rubric

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(self, session: Any, events: list[Any]) -> ComputeResult:
        """Compute all cognitive metrics for a closed session.

        Args:
            session: CognitiveSession ORM model instance (or duck-typed mock).
            events: List of CognitiveEvent ORM model instances ordered by
                    sequence_number ASC.

        Returns:
            ComputeResult with metrics, evaluation_profile, and reasoning_details.
        """
        now = datetime.now(tz=timezone.utc)
        total = len(events)

        n1 = self._compute_n1(events, total)
        n2 = self._compute_n2(events, total)
        n3 = self._compute_n3(events, total)
        dependency_score = self._compute_dependency_score(events)
        n4 = self._compute_n4(events, total, dependency_score)
        help_seeking_ratio, autonomy_index = self._compute_ratios(events, total)
        qe_quality_prompt, qe_critical_eval, qe_integration, qe_verification = (
            self._compute_qe(events)
        )
        qe_score = self._compute_qe_composite(
            qe_quality_prompt, qe_critical_eval, qe_integration, qe_verification
        )
        success_efficiency = self._compute_success_efficiency(events)
        reflection_score = self._compute_reflection_score(events)
        risk_level = self._derive_risk_level(n1, n2, n3, n4, dependency_score, qe_score)
        evaluation_profile = self._build_evaluation_profile(
            n1, n2, n3, n4, qe_score, risk_level, now
        )

        metrics = MetricsDict(
            n1_comprehension_score=n1,
            n2_strategy_score=n2,
            n3_validation_score=n3,
            n4_ai_interaction_score=n4,
            total_interactions=total,
            help_seeking_ratio=help_seeking_ratio,
            autonomy_index=autonomy_index,
            qe_score=qe_score,
            qe_quality_prompt=qe_quality_prompt,
            qe_critical_evaluation=qe_critical_eval,
            qe_integration=qe_integration,
            qe_verification=qe_verification,
            dependency_score=dependency_score,
            reflection_score=reflection_score,
            success_efficiency=success_efficiency,
            risk_level=risk_level,
            computed_at=now,
        )

        reasoning_details = self._build_reasoning_details(session, events, metrics, now)

        logger.info(
            "Metrics computed",
            extra={
                "session_id": str(getattr(session, "id", "unknown")),
                "total_events": total,
                "risk_level": risk_level,
                "n1": str(n1),
                "n2": str(n2),
                "n3": str(n3),
                "n4": str(n4),
                "qe": str(qe_score),
            },
        )

        return ComputeResult(
            metrics=metrics,
            evaluation_profile=evaluation_profile,
            reasoning_details=reasoning_details,
        )

    def create_reasoning_record(
        self,
        session_id: Any,
        details: dict[str, Any],
        previous_hash: str,
        created_at: datetime,
    ) -> dict[str, Any]:
        """Produce the data dict needed to insert a ReasoningRecord.

        Computes the event_hash from the chain so the record participates
        in the same hash-chain pattern as CognitiveEvents.

        Args:
            session_id: The session UUID.
            details: The reasoning_details from ComputeResult.
            previous_hash: Hash of the preceding chain entry (session_hash or genesis_hash).
            created_at: Timestamp for this record.

        Returns:
            Dict with all ReasoningRecord fields (except id, which DB auto-generates).
        """
        record_type = "metrics_computation"
        details_json = json.dumps(details, default=str, sort_keys=True)
        hash_input = f"{previous_hash}:{record_type}:{details_json}:{created_at.isoformat()}"
        event_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return {
            "session_id": session_id,
            "record_type": record_type,
            "details": details,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            "created_at": created_at,
        }

    # ------------------------------------------------------------------
    # N1 — Comprehension
    # ------------------------------------------------------------------

    def _compute_n1(self, events: list[Any], total: int) -> Decimal | None:
        """N1 score: independent comprehension score (0-100).

        Presence (30): student read the problem at least once.
        Depth (30): N1 events count, up to 3 events contribute 10 points each.
        Quality (40): tutor asked N1-level questions (+20), and/or first
          code.run was not the very first event (+20 = student read before coding).
        """
        if total == 0:
            return None

        # Presence: any reads_problem event
        presence = 30 if any(e.event_type == "reads_problem" for e in events) else 0

        # Depth: count of N1 events (reads_problem + code.snapshot), capped at 3
        n1_count = sum(1 for e in events if e.event_type in _N1_EVENT_TYPES)
        depth = min(30, n1_count * 10)

        # Quality component 1: tutor asked N1-level questions
        quality = 0
        if any(
            e.event_type == "tutor.question_asked"
            and isinstance(e.payload, dict)
            and int(e.payload.get("n4_level", 0) or 0) == 1
            for e in events
        ):
            quality += 20

        # Quality component 2: first code.run is NOT the first overall event
        run_indices = [i for i, e in enumerate(events) if e.event_type in _N3_EVENT_TYPES]
        if run_indices and run_indices[0] > 0:
            quality += 20

        score = presence + depth + quality
        return _clamp(_d2(score))

    # ------------------------------------------------------------------
    # N2 — Strategy
    # ------------------------------------------------------------------

    def _compute_n2(self, events: list[Any], total: int) -> Decimal | None:
        """N2 score: independent strategy score (0-100).

        Presence (30): at least one submission.created event.
        Depth (30): tutor asked N2-level questions (+15), and/or code.run
          events exist and at least one N2-level tutor event precedes them
          by sequence_number (+15).
        Quality (40): submission preceded by code.run (+20), multiple distinct
          event types present (+20).
        """
        if total == 0:
            return None

        n2_events = [e for e in events if e.event_type in _N2_EVENT_TYPES]
        if not n2_events:
            return _d2(0)

        # Presence
        presence = 30

        # Depth component 1: tutor asked N2-level questions
        depth = 0
        if any(
            e.event_type == "tutor.question_asked"
            and isinstance(e.payload, dict)
            and int(e.payload.get("n4_level", 0) or 0) == 2
            for e in events
        ):
            depth += 15

        # Depth component 2: code.run events exist AND at least one N2 tutor
        # event precedes them by sequence_number
        run_events = [e for e in events if e.event_type in _N3_EVENT_TYPES]
        n2_tutor_events = [
            e for e in events
            if e.event_type == "tutor.question_asked"
            and isinstance(e.payload, dict)
            and int(e.payload.get("n4_level", 0) or 0) == 2
        ]
        if run_events and n2_tutor_events:
            run_seqs = [getattr(e, "sequence_number", 0) for e in run_events]
            tutor_seqs = [getattr(e, "sequence_number", 0) for e in n2_tutor_events]
            if any(ts < rs for ts in tutor_seqs for rs in run_seqs):
                depth += 15

        # Quality component 1: submission preceded by code.run
        had_prior_run = any(e.event_type in _N3_EVENT_TYPES for e in events)
        quality = 0
        if had_prior_run:
            quality += 20

        # Quality component 2: multiple distinct event types present
        distinct_types = {e.event_type for e in events}
        if len(distinct_types) >= 2:
            quality += 20

        score = presence + depth + quality
        return _clamp(_d2(score))

    # ------------------------------------------------------------------
    # N3 — Validation
    # ------------------------------------------------------------------

    def _compute_n3(self, events: list[Any], total: int) -> Decimal | None:
        """N3 score: independent validation score (0-100).

        Presence (30): at least one code.run event.
        Depth (30): run count, up to 3 runs contribute 10 points each.
        Quality (40): correction cycle detected — at least one error followed
          by a success (+25), and last run succeeded (+15).
        """
        if total == 0:
            return None

        run_events = [e for e in events if e.event_type in _N3_EVENT_TYPES]
        if not run_events:
            return _d2(0)

        # Presence
        presence = 30

        # Depth: run count capped at 3
        depth = min(30, len(run_events) * 10)

        # Quality: convergence — errors should decrease across runs
        quality = 0
        runs_with_status = [e for e in run_events if isinstance(e.payload, dict)]
        if len(runs_with_status) >= 2:
            errors = [
                1 if e.payload.get("status") == "error" else 0
                for e in runs_with_status
            ]
            # Check if any error was followed by a success (correction cycle)
            had_error_then_success = any(
                errors[i] == 1 and errors[i + 1] == 0
                for i in range(len(errors) - 1)
            )
            if had_error_then_success:
                quality += 25
            if errors[-1] == 0:
                quality += 15

        score = presence + depth + quality
        return _clamp(_d2(score))

    # ------------------------------------------------------------------
    # N4 — AI Interaction quality
    # ------------------------------------------------------------------

    def _compute_n4(
        self,
        events: list[Any],
        total: int,
        dependency_score: Decimal | None,
    ) -> Decimal | None:
        """N4 score: independent AI interaction quality score (0-100).

        Based on prompt type distribution in tutor.question_asked events:
        - reflective_ratio = (exploratory + verifier) / total  → max 70 pts
        - bonus for any verification behaviour (+15)
        - bonus for using multiple prompt types (+15)
        - penalized by dependency_score using rubric's dependency_penalty
        """
        tutor_events = [e for e in events if e.event_type in _N4_EVENT_TYPES]
        if not tutor_events:
            return None  # N4 not applicable without AI interaction

        # Collect prompt types from payload
        prompt_types = [
            e.payload.get("prompt_type", "exploratory")
            for e in tutor_events
            if isinstance(e.payload, dict)
        ]
        total_prompts = len(prompt_types)
        if total_prompts == 0:
            return _d2(0)

        exploratory_count = sum(1 for pt in prompt_types if pt == "exploratory")
        verifier_count = sum(1 for pt in prompt_types if pt == "verifier")
        generative_count = sum(1 for pt in prompt_types if pt == "generative")

        # Reflective ratio: (exploratory + verifier) / total → base score max 70
        reflective_ratio = (exploratory_count + verifier_count) / total_prompts
        base_score = reflective_ratio * 70.0

        # Bonus: verification behaviour
        if verifier_count > 0:
            base_score += 15.0

        # Bonus: diversity (student used multiple distinct prompt types)
        types_used = sum(
            1
            for c in [exploratory_count, verifier_count, generative_count]
            if c > 0
        )
        if types_used >= 2:
            base_score += 15.0

        # Apply dependency penalty
        penalty = float(self._rubric.quality_factors.n4.dependency_penalty)
        dep = float(dependency_score) if dependency_score is not None else 0.0
        penalized = base_score * (1.0 - penalty * dep)

        return _clamp(_d2(penalized))

    # ------------------------------------------------------------------
    # Qe sub-scores
    # ------------------------------------------------------------------

    def _compute_qe(
        self, events: list[Any]
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
        """Compute the four Qe sub-scores.

        Returns:
            (qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification)
        """
        tutor_ask_events = [e for e in events if e.event_type in _N4_EVENT_TYPES]
        run_events = [e for e in events if e.event_type in _N3_EVENT_TYPES]
        tutor_resp_events = [e for e in events if e.event_type in _TUTOR_RESPONSE_TYPES]

        # qe_quality_prompt: % of tutor questions with n4_level >= 2
        qe_quality_prompt: Decimal | None = None
        if tutor_ask_events:
            high_quality = sum(
                1
                for e in tutor_ask_events
                if isinstance(e.payload, dict)
                and int(e.payload.get("n4_level", 0) or 0) >= 2
            )
            qe_quality_prompt = _clamp(_d2((high_quality / len(tutor_ask_events)) * 100))

        # qe_critical_evaluation: code.run events after EACH tutor response
        qe_critical_evaluation: Decimal | None = None
        if tutor_resp_events and run_events:
            try:
                resp_seqs = sorted(
                    getattr(e, "sequence_number", 0) for e in tutor_resp_events
                )
                run_seqs = [getattr(e, "sequence_number", 0) for e in run_events]
                responses_followed_by_run = 0
                for resp_seq in resp_seqs:
                    if any(rs > resp_seq for rs in run_seqs):
                        responses_followed_by_run += 1
                total_responses = len(resp_seqs)
                if total_responses > 0:
                    qe_critical_evaluation = _clamp(
                        _d2((responses_followed_by_run / total_responses) * 100)
                    )
                else:
                    qe_critical_evaluation = _d2(0)
            except Exception:
                qe_critical_evaluation = _d2(0)
        elif not tutor_resp_events:
            qe_critical_evaluation = None
        else:
            qe_critical_evaluation = _d2(0)

        # qe_integration: % of post-tutor code.run events that succeeded
        qe_integration: Decimal | None = None
        if tutor_resp_events and run_events:
            try:
                resp_seqs = sorted(
                    getattr(e, "sequence_number", 0) for e in tutor_resp_events
                )
                runs_after_any_resp = [
                    e
                    for e in run_events
                    if any(
                        getattr(e, "sequence_number", 0) > rs for rs in resp_seqs
                    )
                ]
                if runs_after_any_resp:
                    successful = sum(
                        1
                        for e in runs_after_any_resp
                        if isinstance(e.payload, dict)
                        and e.payload.get("status") != "error"
                    )
                    qe_integration = _clamp(_d2((successful / len(runs_after_any_resp)) * 100))
                else:
                    qe_integration = None
            except Exception:
                qe_integration = None

        # qe_verification: presence of code.run events after any code change
        # Approximated as: runs / max(runs, 1) * 100 when there are multiple runs
        # (multiple run attempts indicate verification behaviour)
        qe_verification: Decimal | None = None
        if run_events:
            num_runs = len(run_events)
            if num_runs >= 2:
                # Multiple runs after changes = active verification
                qe_verification = _clamp(_d2(min(100.0, (num_runs / 2.0) * 100.0)))
            else:
                qe_verification = _d2(0)

        return qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification

    def _compute_qe_composite(
        self,
        qe_quality_prompt: Decimal | None,
        qe_critical_evaluation: Decimal | None,
        qe_integration: Decimal | None,
        qe_verification: Decimal | None,
    ) -> Decimal | None:
        """Compute composite Qe as the mean of available sub-scores."""
        available = [
            s
            for s in [qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification]
            if s is not None
        ]
        if not available:
            return None
        return _clamp(_d2(sum(float(s) for s in available) / len(available)))

    # ------------------------------------------------------------------
    # Ratios
    # ------------------------------------------------------------------

    def _compute_ratios(
        self, events: list[Any], total: int
    ) -> tuple[Decimal | None, Decimal | None]:
        """Compute help_seeking_ratio and autonomy_index."""
        if total == 0:
            return None, None

        tutor_count = sum(
            1 for e in events if e.event_type in _N4_EVENT_TYPES | _TUTOR_RESPONSE_TYPES
        )
        help_ratio = _d3(tutor_count / total)
        autonomy = _d3(1.0 - float(help_ratio))
        return help_ratio, autonomy

    def _compute_dependency_score(self, events: list[Any]) -> Decimal | None:
        """Compute dependency_score: fraction of N4 events with sub_classification == 'dependent'."""
        tutor_events = [e for e in events if e.event_type in _N4_EVENT_TYPES]
        if not tutor_events:
            return None

        dependent_count = sum(
            1
            for e in tutor_events
            if isinstance(e.payload, dict)
            and e.payload.get("sub_classification") == "dependent"
        )
        return _d3(dependent_count / len(tutor_events))

    def _compute_success_efficiency(self, events: list[Any]) -> Decimal | None:
        """Compute success_efficiency: successful runs / total runs * 100."""
        run_events = [e for e in events if e.event_type in _N3_EVENT_TYPES]
        if not run_events:
            return None

        successful = sum(
            1
            for e in run_events
            if isinstance(e.payload, dict) and e.payload.get("status") != "error"
        )
        return _clamp(_d2((successful / len(run_events)) * 100))

    def _compute_reflection_score(self, events: list[Any]) -> Decimal | None:
        """Compute reflection_score from reflection.submitted events.

        Factors: number of fields filled (max 5), presence of
        difficulty_perception and confidence_level in payload.
        """
        reflection_events = [e for e in events if e.event_type == "reflection.submitted"]
        if not reflection_events:
            return None

        last_reflection = reflection_events[-1]
        payload = last_reflection.payload if isinstance(last_reflection.payload, dict) else {}

        fields_present = 0
        for field in (
            "difficulty_perception",
            "strategy_description",
            "ai_usage_evaluation",
            "what_would_change",
            "confidence_level",
        ):
            val = payload.get(field)
            if val is not None and val != "" and val != 0:
                fields_present += 1

        base = (fields_present / 5.0) * 80.0

        difficulty = payload.get("difficulty_perception")
        confidence = payload.get("confidence_level")
        if difficulty is not None and confidence is not None:
            try:
                diff_val = int(difficulty)
                conf_val = int(confidence)
                if 1 <= diff_val <= 5 and 1 <= conf_val <= 5:
                    base += 20.0
            except (TypeError, ValueError):
                pass

        return _clamp(_d2(base))

    # ------------------------------------------------------------------
    # Risk level
    # ------------------------------------------------------------------

    def _derive_risk_level(
        self,
        n1: Decimal | None,
        n2: Decimal | None,
        n3: Decimal | None,
        n4: Decimal | None,
        dependency_score: Decimal | None,
        qe_score: Decimal | None = None,
    ) -> str:
        """Classify risk level based on rubric thresholds.

        Precedence: critical > high > medium > low.
        """
        rt = self._rubric.risk_thresholds
        dep = float(dependency_score) if dependency_score is not None else 0.0
        n_scores = [float(s) for s in [n1, n2, n3, n4] if s is not None]
        min_n_score = min(n_scores) if n_scores else 100.0
        n4_score = float(n4) if n4 is not None else 100.0
        qe_val = float(qe_score) if qe_score is not None else 100.0

        # Critical
        crit = rt.critical
        if (
            crit.dependency_score_min is not None and dep >= crit.dependency_score_min
        ) or (crit.n4_score_max is not None and n4_score <= crit.n4_score_max):
            return "critical"

        # High
        high = rt.high
        if (
            high.dependency_score_min is not None and dep >= high.dependency_score_min
        ) or (high.any_n_score_max is not None and min_n_score <= high.any_n_score_max):
            return "high"

        # Medium
        med = rt.medium
        if med.any_n_score_max is not None and min_n_score <= med.any_n_score_max:
            return "medium"
        if med.qe_score_max is not None and qe_val <= med.qe_score_max:
            return "medium"

        return "low"

    # ------------------------------------------------------------------
    # Evaluation profile (n4_final_score JSONB)
    # ------------------------------------------------------------------

    def _build_evaluation_profile(
        self,
        n1: Decimal | None,
        n2: Decimal | None,
        n3: Decimal | None,
        n4: Decimal | None,
        qe: Decimal | None,
        risk_level: str,
        computed_at: datetime,
    ) -> dict[str, Any]:
        """Build the JSONB dict stored in cognitive_sessions.n4_final_score."""
        weights = self._rubric.weights
        weight_map = {
            "n1": weights.n1_comprehension,
            "n2": weights.n2_strategy,
            "n3": weights.n3_validation,
            "n4": weights.n4_ai_interaction,
            "qe": weights.qe,
        }
        score_map = {"n1": n1, "n2": n2, "n3": n3, "n4": n4, "qe": qe}

        weighted_total = Decimal("0")
        for key, w in weight_map.items():
            s = score_map[key]
            if s is not None:
                weighted_total += Decimal(str(w)) * s

        return {
            "n1": float(n1) if n1 is not None else None,
            "n2": float(n2) if n2 is not None else None,
            "n3": float(n3) if n3 is not None else None,
            "n4": float(n4) if n4 is not None else None,
            "qe": float(qe) if qe is not None else None,
            "weighted_total": float(_d2(weighted_total)),
            "weights": {
                "n1": weights.n1_comprehension,
                "n2": weights.n2_strategy,
                "n3": weights.n3_validation,
                "n4": weights.n4_ai_interaction,
                "qe": weights.qe,
            },
            "risk_level": risk_level,
            "computed_at": computed_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Reasoning record details
    # ------------------------------------------------------------------

    def _build_reasoning_details(
        self,
        session: Any,
        events: list[Any],
        metrics: MetricsDict,
        computed_at: datetime,
    ) -> dict[str, Any]:
        """Build the full reasoning details stored in ReasoningRecord."""
        event_type_counts: dict[str, int] = {}
        for e in events:
            event_type_counts[e.event_type] = event_type_counts.get(e.event_type, 0) + 1

        return {
            "session_id": str(getattr(session, "id", "unknown")),
            "total_events": len(events),
            "event_type_counts": event_type_counts,
            "scores": {
                "n1_comprehension_score": float(metrics.n1_comprehension_score)
                if metrics.n1_comprehension_score is not None
                else None,
                "n2_strategy_score": float(metrics.n2_strategy_score)
                if metrics.n2_strategy_score is not None
                else None,
                "n3_validation_score": float(metrics.n3_validation_score)
                if metrics.n3_validation_score is not None
                else None,
                "n4_ai_interaction_score": float(metrics.n4_ai_interaction_score)
                if metrics.n4_ai_interaction_score is not None
                else None,
                "qe_score": float(metrics.qe_score) if metrics.qe_score is not None else None,
                "dependency_score": float(metrics.dependency_score)
                if metrics.dependency_score is not None
                else None,
            },
            "risk_level": metrics.risk_level,
            "computed_at": computed_at.isoformat(),
            "rubric_weights": {
                "n1": self._rubric.weights.n1_comprehension,
                "n2": self._rubric.weights.n2_strategy,
                "n3": self._rubric.weights.n3_validation,
                "n4": self._rubric.weights.n4_ai_interaction,
                "qe": self._rubric.weights.qe,
            },
        }
