"""MetricsEngine v2 — pure computation service for N1-N4 cognitive metrics.

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

_ENGINE_VERSION = "2.0"

_TWO = Decimal("1E-2")
_THREE = Decimal("1E-3")


def _d2(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(_TWO, rounding=ROUND_HALF_UP)


def _d3(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(_THREE, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, lo: Decimal = Decimal("0"), hi: Decimal = Decimal("100")) -> Decimal:
    return max(lo, min(hi, value))


def _get_n4_level(event: Any) -> int | None:
    attr = getattr(event, "n4_level", None)
    if isinstance(attr, int):
        return attr
    if isinstance(getattr(event, "payload", None), dict):
        val = event.payload.get("n4_level")
        if val is not None:
            return int(val)
    return None


def _events_by_level(events: list[Any], level: int) -> list[Any]:
    return [e for e in events if _get_n4_level(e) == level]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class MetricsDict:
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
    engine_version: str = _ENGINE_VERSION
    computed_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

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
            "engine_version": self.engine_version,
            "computed_at": self.computed_at,
        }


@dataclass
class ComputeResult:
    metrics: MetricsDict
    evaluation_profile: dict[str, Any]
    reasoning_details: dict[str, Any]
    score_breakdown: dict[str, list[dict[str, Any]]]


# ---------------------------------------------------------------------------
# MetricsEngine v2
# ---------------------------------------------------------------------------


class MetricsEngine:
    """Pure computation engine for N1-N4 cognitive metrics (v2).

    Uses n4_level attribute on events instead of hardcoded event type sets.
    """

    def __init__(self, rubric: RubricConfig) -> None:
        self._rubric = rubric

    def compute(self, session: Any, events: list[Any]) -> ComputeResult:
        now = datetime.now(tz=timezone.utc)
        total = len(events)

        breakdown: dict[str, list[dict[str, Any]]] = {}

        n1, breakdown["n1"] = self._compute_n1(events, total)
        n2, breakdown["n2"] = self._compute_n2(events, total)
        n3, breakdown["n3"] = self._compute_n3(events, total)
        dependency_score = self._compute_dependency_score(events)
        n4, breakdown["n4"] = self._compute_n4(events, total, dependency_score)
        help_seeking_ratio, autonomy_index = self._compute_ratios(events, total)
        qe_quality_prompt, qe_critical_eval, qe_integration, qe_verification = (
            self._compute_qe(events)
        )
        # B9: Qe composite from per-level sub-scores
        qe_n1 = self._compute_qe_n1(events)
        qe_n2 = self._compute_qe_n2(events)
        qe_n3 = self._compute_qe_n3(events)
        # qe_n4 = average of the four existing sub-scores (quality/eval/integration/verification)
        _n4_sub = [
            s for s in [qe_quality_prompt, qe_critical_eval, qe_integration, qe_verification]
            if s is not None
        ]
        qe_n4 = _clamp(_d2(sum(float(s) for s in _n4_sub) / len(_n4_sub))) if _n4_sub else None
        qe_score = self._compute_qe_composite(qe_n1, qe_n2, qe_n3, qe_n4)
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
            engine_version=_ENGINE_VERSION,
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
                "engine_version": _ENGINE_VERSION,
            },
        )

        return ComputeResult(
            metrics=metrics,
            evaluation_profile=evaluation_profile,
            reasoning_details=reasoning_details,
            score_breakdown=breakdown,
        )

    def create_reasoning_record(
        self,
        session_id: Any,
        details: dict[str, Any],
        previous_hash: str,
        created_at: datetime,
    ) -> dict[str, Any]:
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

    def _compute_n1(self, events: list[Any], total: int) -> tuple[Decimal | None, list[dict]]:
        """N1 v2: presence from reading_time thresholds, depth from reread + N1 questions,
        quality from first-event-not-run + exploratory N1 question + reflection."""
        bd: list[dict[str, Any]] = []
        if total == 0:
            return None, bd

        # Presence: reading_time >= 15s → +15, >= 45s → +15 more
        reading_events = [e for e in events if e.event_type == "problem.reading_time"]
        max_reading_ms = 0
        for e in reading_events:
            if isinstance(e.payload, dict):
                max_reading_ms = max(max_reading_ms, int(e.payload.get("reading_duration_ms", 0) or 0))

        has_reads_problem = any(e.event_type == "reads_problem" for e in events)
        if not reading_events and has_reads_problem:
            max_reading_ms = 16000

        presence = 0
        read_15 = max_reading_ms >= 15000
        read_45 = max_reading_ms >= 45000
        if read_15:
            presence += 15
        if read_45:
            presence += 15
        bd.append({"condition": "Leyo el enunciado >= 15 seg", "met": read_15, "points": 15 if read_15 else 0})
        bd.append({"condition": "Leyo el enunciado >= 45 seg", "met": read_45, "points": 15 if read_45 else 0})

        # Depth: reread (+15), N1 tutor question (+15)
        depth = 0
        has_reread = any(e.event_type == "problem.reread" for e in events)
        if has_reread:
            depth += 15
        bd.append({"condition": "Releyo el enunciado despues de codear", "met": has_reread, "points": 15 if has_reread else 0})

        has_n1_question = any(
            e.event_type == "tutor.question_asked" and _get_n4_level(e) == 1
            for e in events
        )
        if has_n1_question:
            depth += 15
        bd.append({"condition": "Pregunta de comprension al tutor", "met": has_n1_question, "points": 15 if has_n1_question else 0})

        # Quality: first event not code.run (+15), exploratory N1 question (+15), reflection with difficulty (+10)
        quality = 0
        run_indices = [i for i, e in enumerate(events) if e.event_type == "code.run"]
        first_not_run = bool(run_indices) and run_indices[0] > 0
        if not run_indices:
            first_not_run = True
        if first_not_run:
            quality += 15
        bd.append({"condition": "No arranco directamente ejecutando codigo", "met": first_not_run, "points": 15 if first_not_run else 0})

        has_exploratory_n1 = any(
            e.event_type == "tutor.question_asked"
            and _get_n4_level(e) == 1
            and isinstance(e.payload, dict)
            and e.payload.get("prompt_type") == "exploratory"
            for e in events
        )
        if has_exploratory_n1:
            quality += 15
        bd.append({"condition": "Pregunta exploratoria N1 al tutor", "met": has_exploratory_n1, "points": 15 if has_exploratory_n1 else 0})

        has_reflection_difficulty = any(
            e.event_type == "reflection.submitted"
            and isinstance(e.payload, dict)
            and e.payload.get("difficulty_perception") is not None
            for e in events
        )
        if has_reflection_difficulty:
            quality += 10
        bd.append({"condition": "Reflexion con percepcion de dificultad", "met": has_reflection_difficulty, "points": 10 if has_reflection_difficulty else 0})

        score = presence + depth + quality
        return _clamp(_d2(score)), bd

    # ------------------------------------------------------------------
    # N2 — Strategy
    # ------------------------------------------------------------------

    def _compute_n2(self, events: list[Any], total: int) -> tuple[Decimal | None, list[dict]]:
        """N2 v2: presence requires pseudocode OR N2 tutor question."""
        bd: list[dict[str, Any]] = []
        if total == 0:
            return None, bd

        # Presence: pseudocode.written (+20) or N2 tutor question (+10)
        presence = 0
        has_pseudocode = any(e.event_type == "pseudocode.written" for e in events)
        if has_pseudocode:
            presence += 20
        bd.append({"condition": "Escribio pseudocodigo/plan", "met": has_pseudocode, "points": 20 if has_pseudocode else 0})

        has_n2_question = any(
            e.event_type == "tutor.question_asked" and _get_n4_level(e) == 2
            for e in events
        )
        if has_n2_question:
            presence += 10
        bd.append({"condition": "Pregunta de estrategia al tutor", "met": has_n2_question, "points": 10 if has_n2_question else 0})

        if presence == 0:
            bd.append({"condition": "Sin evidencia de planificacion", "met": True, "points": 0})
            return _d2(0), bd

        # Depth: N2 question precedes code.run (+15), multiple N2 question types (+15)
        depth = 0
        run_events = [e for e in events if e.event_type == "code.run"]
        n2_tutor_events = [
            e for e in events
            if e.event_type == "tutor.question_asked" and _get_n4_level(e) == 2
        ]

        n2_precedes_run = False
        if run_events and n2_tutor_events:
            run_seqs = [getattr(e, "sequence_number", 0) for e in run_events]
            tutor_seqs = [getattr(e, "sequence_number", 0) for e in n2_tutor_events]
            n2_precedes_run = any(ts < rs for ts in tutor_seqs for rs in run_seqs)
        if n2_precedes_run:
            depth += 15
        bd.append({"condition": "Pregunta N2 precede ejecucion de codigo", "met": n2_precedes_run, "points": 15 if n2_precedes_run else 0})

        n2_events_all = _events_by_level(events, 2)
        multiple_n2_types = len({e.event_type for e in n2_events_all}) >= 2
        if multiple_n2_types:
            depth += 15
        bd.append({"condition": "Multiples tipos de evidencia N2", "met": multiple_n2_types, "points": 15 if multiple_n2_types else 0})

        # Quality: code.run after pseudocode (+20), incremental snapshots (+20)
        quality = 0
        has_run_after_pseudo = False
        if has_pseudocode and run_events:
            pseudo_events = [e for e in events if e.event_type == "pseudocode.written"]
            if pseudo_events:
                pseudo_seq = getattr(pseudo_events[0], "sequence_number", 0)
                has_run_after_pseudo = any(getattr(e, "sequence_number", 0) > pseudo_seq for e in run_events)
        if has_run_after_pseudo:
            quality += 20
        bd.append({"condition": "Ejecuto codigo despues del pseudocodigo", "met": has_run_after_pseudo, "points": 20 if has_run_after_pseudo else 0})

        snapshots = [e for e in events if e.event_type == "code.snapshot"]
        incremental = len(snapshots) >= 3
        if incremental:
            quality += 20
        bd.append({"condition": "Evolucion incremental (3+ snapshots)", "met": incremental, "points": 20 if incremental else 0})

        score = presence + depth + quality
        return _clamp(_d2(score)), bd

    # ------------------------------------------------------------------
    # N3 — Validation
    # ------------------------------------------------------------------

    def _compute_n3(self, events: list[Any], total: int) -> tuple[Decimal | None, list[dict]]:
        """N3 v2: adds bonus for test.manual_case and is_edge_case."""
        bd: list[dict[str, Any]] = []
        if total == 0:
            return None, bd

        run_events = [e for e in events if e.event_type == "code.run"]
        if not run_events:
            bd.append({"condition": "Sin ejecuciones de codigo", "met": True, "points": 0})
            return _d2(0), bd

        # Presence
        presence = 0
        has_one_run = len(run_events) >= 1
        has_two_runs = len(run_events) >= 2
        if has_one_run:
            presence += 15
        if has_two_runs:
            presence += 15
        bd.append({"condition": "Al menos una ejecucion", "met": has_one_run, "points": 15 if has_one_run else 0})
        bd.append({"condition": "Al menos dos ejecuciones", "met": has_two_runs, "points": 15 if has_two_runs else 0})

        # Depth: correction cycle (+15), test.manual_case (+15)
        depth = 0
        runs_with_status = [e for e in run_events if isinstance(e.payload, dict)]
        had_error_then_success = False
        if len(runs_with_status) >= 2:
            errors = [
                1 if e.payload.get("status") == "error" else 0
                for e in runs_with_status
            ]
            had_error_then_success = any(
                errors[i] == 1 and errors[i + 1] == 0
                for i in range(len(errors) - 1)
            )
        if had_error_then_success:
            depth += 15
        bd.append({"condition": "Ciclo error -> correccion -> exito", "met": had_error_then_success, "points": 15 if had_error_then_success else 0})

        has_manual_test = any(e.event_type == "test.manual_case" for e in events)
        if has_manual_test:
            depth += 15
        bd.append({"condition": "Escribio tests manuales propios", "met": has_manual_test, "points": 15 if has_manual_test else 0})

        # Quality: last run succeeded (+15), N3 tutor question (+10), edge case tested (+15)
        quality = 0
        last_run_success = False
        if runs_with_status:
            last_run_success = runs_with_status[-1].payload.get("status") != "error"
        if last_run_success:
            quality += 15
        bd.append({"condition": "Ultima ejecucion exitosa", "met": last_run_success, "points": 15 if last_run_success else 0})

        has_n3_question = any(
            e.event_type == "tutor.question_asked" and _get_n4_level(e) == 3
            for e in events
        )
        if has_n3_question:
            quality += 10
        bd.append({"condition": "Pregunta de debugging al tutor", "met": has_n3_question, "points": 10 if has_n3_question else 0})

        has_edge_case = any(
            e.event_type == "test.manual_case"
            and isinstance(e.payload, dict)
            and e.payload.get("is_edge_case") is True
            for e in events
        )
        if has_edge_case:
            quality += 15
        bd.append({"condition": "Probo caso limite", "met": has_edge_case, "points": 15 if has_edge_case else 0})

        score = presence + depth + quality
        return _clamp(_d2(score)), bd

    # ------------------------------------------------------------------
    # N4 — AI Interaction quality
    # ------------------------------------------------------------------

    def _compute_n4(
        self,
        events: list[Any],
        total: int,
        dependency_score: Decimal | None,
    ) -> tuple[Decimal | None, list[dict]]:
        """N4 v2: integrates prompt.reformulated and code.accepted_from_tutor."""
        bd: list[dict[str, Any]] = []

        tutor_events = [e for e in events if e.event_type == "tutor.question_asked"]
        if not tutor_events:
            bd.append({"condition": "Sin interaccion con tutor", "met": True, "points": 0})
            return None, bd

        prompt_types = [
            e.payload.get("prompt_type", "exploratory")
            for e in tutor_events
            if isinstance(e.payload, dict)
        ]
        total_prompts = len(prompt_types)
        if total_prompts == 0:
            return _d2(0), bd

        exploratory_count = sum(1 for pt in prompt_types if pt == "exploratory")
        verifier_count = sum(1 for pt in prompt_types if pt == "verifier")

        reflective_ratio = (exploratory_count + verifier_count) / total_prompts
        base_score = reflective_ratio * 70.0
        bd.append({"condition": f"Ratio reflexivo ({exploratory_count + verifier_count}/{total_prompts})", "met": reflective_ratio > 0.5, "points": round(base_score, 1)})

        # Bonus: verification behaviour
        has_verifier = verifier_count > 0
        if has_verifier:
            base_score += 15.0
        bd.append({"condition": "Uso prompts verificadores", "met": has_verifier, "points": 15 if has_verifier else 0})

        # Bonus: prompt reformulation (replaces diversity bonus)
        has_reformulation = any(e.event_type == "prompt.reformulated" for e in events)
        if has_reformulation:
            base_score += 10.0
            bd.append({"condition": "Reformulo preguntas al tutor", "met": True, "points": 10})
        else:
            types_used = len({pt for pt in prompt_types})
            has_diversity = types_used >= 2
            if has_diversity:
                base_score += 10.0
            bd.append({"condition": "Diversidad de tipos de prompt", "met": has_diversity, "points": 10 if has_diversity else 0})

        # Penalty: dependency + code accepted without modification
        penalty = float(self._rubric.quality_factors.n4.dependency_penalty)
        dep = float(dependency_score) if dependency_score is not None else 0.0

        # Extra penalty for unmodified code acceptance
        unmodified_accepts = [
            e for e in events
            if e.event_type == "code.accepted_from_tutor"
            and isinstance(e.payload, dict)
            and not e.payload.get("was_modified_after", True)
        ]
        if unmodified_accepts:
            dep = min(1.0, dep * 1.5)
            bd.append({"condition": "Copio codigo del tutor sin modificar", "met": True, "points": -round(base_score * penalty * dep - base_score * penalty * (dep / 1.5), 1)})

        penalized = base_score * (1.0 - penalty * dep)
        bd.append({"condition": f"Penalizacion por dependencia ({dep:.2f})", "met": dep > 0.3, "points": -round(base_score - penalized, 1)})

        return _clamp(_d2(penalized)), bd

    # ------------------------------------------------------------------
    # Qe sub-scores
    # ------------------------------------------------------------------

    def _compute_qe(
        self, events: list[Any]
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
        tutor_ask_events = [e for e in events if e.event_type == "tutor.question_asked"]
        run_events = [e for e in events if e.event_type == "code.run"]
        tutor_resp_events = [e for e in events if e.event_type == "tutor.response_received"]
        snapshot_events = [e for e in events if e.event_type == "code.snapshot"]

        # qe_quality_prompt: % of tutor questions with n4_level >= 2
        qe_quality_prompt: Decimal | None = None
        if tutor_ask_events:
            high_quality = sum(
                1
                for e in tutor_ask_events
                if _get_n4_level(e) is not None and _get_n4_level(e) >= 2
            )
            qe_quality_prompt = _clamp(_d2((high_quality / len(tutor_ask_events)) * 100))

        # qe_critical_evaluation: code.run events after EACH tutor response
        qe_critical_evaluation: Decimal | None = None
        if tutor_resp_events and run_events:
            resp_seqs = sorted(getattr(e, "sequence_number", 0) for e in tutor_resp_events)
            run_seqs = sorted(getattr(e, "sequence_number", 0) for e in run_events)
            responses_followed_by_run = 0
            for resp_seq in resp_seqs:
                if any(rs > resp_seq for rs in run_seqs):
                    responses_followed_by_run += 1
            if resp_seqs:
                qe_critical_evaluation = _clamp(
                    _d2((responses_followed_by_run / len(resp_seqs)) * 100)
                )
        elif not tutor_resp_events:
            qe_critical_evaluation = None

        # qe_integration: % of post-tutor runs that succeeded
        # Each run is attributed to the MOST RECENT preceding tutor response
        qe_integration: Decimal | None = None
        if tutor_resp_events and run_events:
            resp_seqs = sorted(getattr(e, "sequence_number", 0) for e in tutor_resp_events)
            post_tutor_runs = []
            for e in run_events:
                run_seq = getattr(e, "sequence_number", 0)
                preceding_resps = [rs for rs in resp_seqs if rs < run_seq]
                if preceding_resps:
                    post_tutor_runs.append(e)
            if post_tutor_runs:
                successful = sum(
                    1
                    for e in post_tutor_runs
                    if isinstance(e.payload, dict) and e.payload.get("status") != "error"
                )
                qe_integration = _clamp(_d2((successful / len(post_tutor_runs)) * 100))

        # qe_verification: ratio of snapshots followed by a run
        qe_verification: Decimal | None = None
        if snapshot_events:
            run_seqs = sorted(getattr(e, "sequence_number", 0) for e in run_events)
            snapshots_followed = 0
            for snap in snapshot_events:
                snap_seq = getattr(snap, "sequence_number", 0)
                if any(rs > snap_seq for rs in run_seqs):
                    snapshots_followed += 1
            qe_verification = _clamp(_d2((snapshots_followed / len(snapshot_events)) * 100))
        elif run_events:
            qe_verification = _clamp(_d2(min(100.0, len(run_events) * 50.0)))

        return qe_quality_prompt, qe_critical_evaluation, qe_integration, qe_verification

    # ------------------------------------------------------------------
    # Qe level-specific sub-scores (B9)
    # ------------------------------------------------------------------

    def _compute_qe_n1(self, events: list[Any]) -> Decimal | None:
        """Qe sub-score for N1 — reading engagement evidence.

        Scoring:
          - problem.reading_time with reading_duration_ms > 10000 → +50
          - problem.reread event present → +50
        Clamped to 0-100.
        """
        if not events:
            return None

        score = 0

        reading_events = [e for e in events if e.event_type == "problem.reading_time"]
        has_adequate_reading = False
        for e in reading_events:
            if isinstance(e.payload, dict):
                duration_ms = int(e.payload.get("reading_duration_ms", 0) or 0)
                if duration_ms > 10000:
                    has_adequate_reading = True
                    break
        if has_adequate_reading:
            score += 50

        has_reread = any(e.event_type == "problem.reread" for e in events)
        if has_reread:
            score += 50

        if score == 0 and not reading_events and not has_reread:
            return None

        return _clamp(_d2(score))

    def _compute_qe_n2(self, events: list[Any]) -> Decimal | None:
        """Qe sub-score for N2 — planning evidence.

        Scoring:
          - pseudocode.written event → +70
          - planning-related tutor question (prompt_type == "exploratory" AND n4_level <= 2) → +30
        Clamped to 0-100.
        """
        if not events:
            return None

        score = 0

        has_pseudocode = any(e.event_type == "pseudocode.written" for e in events)
        if has_pseudocode:
            score += 70

        has_planning_question = any(
            e.event_type == "tutor.question_asked"
            and isinstance(e.payload, dict)
            and e.payload.get("prompt_type") == "exploratory"
            and _get_n4_level(e) is not None
            and _get_n4_level(e) <= 2
            for e in events
        )
        if has_planning_question:
            score += 30

        tutor_events = [e for e in events if e.event_type == "tutor.question_asked"]
        pseudocode_events = [e for e in events if e.event_type == "pseudocode.written"]
        if not tutor_events and not pseudocode_events:
            return None

        return _clamp(_d2(score))

    def _compute_qe_n3(self, events: list[Any]) -> Decimal | None:
        """Qe sub-score for N3 — verification behaviour.

        Scoring:
          - post-tutor code.run ratio (qe_critical_evaluation) → weighted 50%
          - test.manual_case event present → +50
        Clamped to 0-100.
        """
        if not events:
            return None

        tutor_resp_events = [e for e in events if e.event_type == "tutor.response_received"]
        run_events = [e for e in events if e.event_type == "code.run"]

        # Re-use the critical evaluation ratio logic
        qe_critical_eval: Decimal | None = None
        if tutor_resp_events and run_events:
            resp_seqs = sorted(getattr(e, "sequence_number", 0) for e in tutor_resp_events)
            run_seqs = sorted(getattr(e, "sequence_number", 0) for e in run_events)
            responses_followed_by_run = 0
            for resp_seq in resp_seqs:
                if any(rs > resp_seq for rs in run_seqs):
                    responses_followed_by_run += 1
            if resp_seqs:
                qe_critical_eval = _clamp(
                    _d2((responses_followed_by_run / len(resp_seqs)) * 100)
                )

        has_manual_test = any(e.event_type == "test.manual_case" for e in events)

        if qe_critical_eval is None and not has_manual_test:
            return None

        score = Decimal("0")
        if qe_critical_eval is not None:
            score += qe_critical_eval * Decimal("0.5")
        if has_manual_test:
            score += Decimal("50")

        return _clamp(_d2(score))

    def _compute_qe_composite(
        self,
        qe_n1: Decimal | None,
        qe_n2: Decimal | None,
        qe_n3: Decimal | None,
        qe_n4: Decimal | None,
    ) -> Decimal | None:
        """Weighted composite of the four Qe level scores.

        Weights come from rubric.qe_weights. A None score for a level
        contributes 0 to numerator but its weight is still included in
        the denominator — missing evidence is penalised, not ignored.

        Returns None only when ALL four inputs are None (no evidence at all).
        """
        w = self._rubric.qe_weights
        level_pairs: list[tuple[float, Decimal | None]] = [
            (w.n1, qe_n1),
            (w.n2, qe_n2),
            (w.n3, qe_n3),
            (w.n4, qe_n4),
        ]

        total_weight = sum(weight for weight, _ in level_pairs)
        if total_weight == 0:
            return None

        all_none = all(score is None for _, score in level_pairs)
        if all_none:
            return None

        weighted_sum = sum(
            weight * (float(score) if score is not None else 0.0)
            for weight, score in level_pairs
        )
        return _clamp(_d2(weighted_sum / total_weight))

    # ------------------------------------------------------------------
    # Ratios
    # ------------------------------------------------------------------

    def _compute_ratios(
        self, events: list[Any], total: int
    ) -> tuple[Decimal | None, Decimal | None]:
        if total == 0:
            return None, None
        tutor_count = sum(
            1 for e in events
            if e.event_type in ("tutor.question_asked", "tutor.response_received")
        )
        help_ratio = _d3(tutor_count / total)
        autonomy = _d3(1.0 - float(help_ratio))
        return help_ratio, autonomy

    def _compute_dependency_score(self, events: list[Any]) -> Decimal | None:
        tutor_events = [e for e in events if e.event_type == "tutor.question_asked"]
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
        run_events = [e for e in events if e.event_type == "code.run"]
        if not run_events:
            return None
        successful = sum(
            1
            for e in run_events
            if isinstance(e.payload, dict) and e.payload.get("status") != "error"
        )
        return _clamp(_d2((successful / len(run_events)) * 100))

    def _compute_reflection_score(self, events: list[Any]) -> Decimal | None:
        reflection_events = [e for e in events if e.event_type == "reflection.submitted"]
        if not reflection_events:
            return None

        last_reflection = reflection_events[-1]
        payload = last_reflection.payload if isinstance(last_reflection.payload, dict) else {}

        fields_present = 0
        for f in (
            "difficulty_perception",
            "strategy_description",
            "ai_usage_evaluation",
            "what_would_change",
            "confidence_level",
        ):
            val = payload.get(f)
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
        rt = self._rubric.risk_thresholds
        dep = float(dependency_score) if dependency_score is not None else 0.0
        # N4=None is excluded (autonomous student), not defaulted to 100
        n_scores = [float(s) for s in [n1, n2, n3] if s is not None]
        if n4 is not None:
            n_scores.append(float(n4))
        min_n_score = min(n_scores) if n_scores else 100.0
        n4_score = float(n4) if n4 is not None else None
        qe_val = float(qe_score) if qe_score is not None else 100.0

        # Critical
        crit = rt.critical
        if crit.dependency_score_min is not None and dep >= crit.dependency_score_min:
            return "critical"
        if n4_score is not None and crit.n4_score_max is not None and n4_score <= crit.n4_score_max:
            return "critical"

        # High
        high = rt.high
        if high.dependency_score_min is not None and dep >= high.dependency_score_min:
            return "high"
        if high.any_n_score_max is not None and min_n_score <= high.any_n_score_max:
            return "high"

        # Medium
        med = rt.medium
        if med.any_n_score_max is not None and min_n_score <= med.any_n_score_max:
            return "medium"
        if med.qe_score_max is not None and qe_val <= med.qe_score_max:
            return "medium"

        return "low"

    # ------------------------------------------------------------------
    # Evaluation profile
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
            "engine_version": _ENGINE_VERSION,
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
            "engine_version": _ENGINE_VERSION,
            "computed_at": computed_at.isoformat(),
            "rubric_weights": {
                "n1": self._rubric.weights.n1_comprehension,
                "n2": self._rubric.weights.n2_strategy,
                "n3": self._rubric.weights.n3_validation,
                "n4": self._rubric.weights.n4_ai_interaction,
                "qe": self._rubric.weights.qe,
            },
        }
