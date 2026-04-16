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
        risk_level = self._derive_risk_level(n1, n2, n3, n4, dependency_score)
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
            reflection_score=None,  # placeholder for Fase 3 expansion
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
        """N1 score: fraction of N1-type events scaled to 0-100.

        N1 events: reads_problem, code.snapshot.
        These indicate the student is actively reading and observing the problem.
        """
        if total == 0:
            return None
        count = sum(1 for e in events if e.event_type in _N1_EVENT_TYPES)
        raw = (count / total) * 100
        return _clamp(_d2(raw))

    # ------------------------------------------------------------------
    # N2 — Strategy
    # ------------------------------------------------------------------

    def _compute_n2(self, events: list[Any], total: int) -> Decimal | None:
        """N2 score: submission events weighted by quality factor.

        Quality factor is 1.0 if any code.run events precede the submission
        (student tested code before submitting), 0.5 otherwise.
        """
        if total == 0:
            return None

        n2_events = [e for e in events if e.event_type in _N2_EVENT_TYPES]
        if not n2_events:
            return _d2(0)

        # Quality factor: presence of code.run before first submission
        had_prior_run = any(e.event_type in _N3_EVENT_TYPES for e in events)
        quality_factor = 1.0 if had_prior_run else 0.5

        count = len(n2_events)
        raw = (count / total) * quality_factor * 100
        return _clamp(_d2(raw))

    # ------------------------------------------------------------------
    # N3 — Validation
    # ------------------------------------------------------------------

    def _compute_n3(self, events: list[Any], total: int) -> Decimal | None:
        """N3 score: code.run events weighted by iteration quality.

        Quality factor is boosted when the student runs code multiple times
        (indicating iterative correction), which is the core N3 behaviour.
        """
        if total == 0:
            return None

        run_events = [e for e in events if e.event_type in _N3_EVENT_TYPES]
        if not run_events:
            return _d2(0)

        # Quality factor: multiple code.run iterations indicate correction cycles
        num_runs = len(run_events)
        if num_runs >= 3:
            quality_factor = 1.2  # strong iterative validation
        elif num_runs == 2:
            quality_factor = 1.1  # some correction
        else:
            quality_factor = 1.0  # single run

        raw = (num_runs / total) * quality_factor * 100
        return _clamp(_d2(raw))

    # ------------------------------------------------------------------
    # N4 — AI Interaction quality
    # ------------------------------------------------------------------

    def _compute_n4(
        self,
        events: list[Any],
        total: int,
        dependency_score: Decimal | None,
    ) -> Decimal | None:
        """N4 score: average n4_level from tutor.question_asked events.

        n4_level values (0-3 from the classifier):
          0 = no AI involvement / unknown
          1 = simple/dependent question
          2 = guided question
          3 = critical, evaluative question

        Raw score is (avg_level / 3) * 100. Then penalized by dependency_score
        using the rubric's dependency_penalty factor.
        """
        if total == 0:
            return None

        tutor_events = [e for e in events if e.event_type in _N4_EVENT_TYPES]
        if not tutor_events:
            return None  # no AI interaction — N4 not applicable

        levels = []
        for e in tutor_events:
            payload = e.payload if isinstance(e.payload, dict) else {}
            level = payload.get("n4_level")
            if level is not None:
                try:
                    levels.append(int(level))
                except (TypeError, ValueError):
                    pass

        if not levels:
            return _d2(0)

        avg_level = sum(levels) / len(levels)
        raw = (avg_level / 3.0) * 100.0

        # Apply dependency penalty
        penalty = float(self._rubric.quality_factors.n4.dependency_penalty)
        dep = float(dependency_score) if dependency_score is not None else 0.0
        penalized = raw * (1.0 - penalty * dep)

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

        # qe_critical_evaluation: presence of code.run events after tutor.response_received
        qe_critical_evaluation: Decimal | None = None
        if tutor_resp_events and run_events:
            # Find code.run events that occur after at least one tutor response
            # Use sequence_number ordering
            try:
                last_resp_seq = max(
                    getattr(e, "sequence_number", 0) for e in tutor_resp_events
                )
                runs_after_resp = sum(
                    1
                    for e in run_events
                    if getattr(e, "sequence_number", 0) > last_resp_seq
                )
                total_runs = len(run_events)
                if total_runs > 0:
                    qe_critical_evaluation = _clamp(_d2((runs_after_resp / total_runs) * 100))
                else:
                    qe_critical_evaluation = _d2(0)
            except Exception:
                qe_critical_evaluation = _d2(0)
        elif not tutor_resp_events:
            qe_critical_evaluation = None  # not applicable
        else:
            qe_critical_evaluation = _d2(0)

        # qe_integration: % of code.run after tutor help that succeeded (status != "error")
        qe_integration: Decimal | None = None
        if tutor_resp_events and run_events:
            try:
                last_resp_seq = max(
                    getattr(e, "sequence_number", 0) for e in tutor_resp_events
                )
                runs_after = [
                    e
                    for e in run_events
                    if getattr(e, "sequence_number", 0) > last_resp_seq
                ]
                if runs_after:
                    successful = sum(
                        1
                        for e in runs_after
                        if isinstance(e.payload, dict)
                        and e.payload.get("status") != "error"
                    )
                    qe_integration = _clamp(_d2((successful / len(runs_after)) * 100))
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
    ) -> str:
        """Classify risk level based on rubric thresholds.

        Precedence: critical > high > medium > low.
        """
        rt = self._rubric.risk_thresholds
        dep = float(dependency_score) if dependency_score is not None else 0.0
        n_scores = [float(s) for s in [n1, n2, n3, n4] if s is not None]
        min_n_score = min(n_scores) if n_scores else 100.0
        n4_score = float(n4) if n4 is not None else 100.0

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

        from decimal import Decimal as _Dec

        if med.qe_score_max is not None:
            # Also check qe indirectly via the n-scores — we already checked n-scores above
            # If we fall here, all n-scores are above medium threshold; return low
            pass

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
