"""Unit tests for MetricsEngine — deterministic scoring.

Uses MagicMock(spec=CognitiveEvent) to create fake events without any
database or FastAPI infrastructure. MetricsEngine is pure Python so
no async is needed here.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.features.cognitive.models import CognitiveEvent, CognitiveSession
from app.features.evaluation.rubric import RubricConfig
from app.features.evaluation.service import MetricsEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    s = MagicMock(spec=CognitiveSession)
    s.id = uuid.uuid4()
    s.student_id = uuid.uuid4()
    s.exercise_id = uuid.uuid4()
    return s


def _make_event(
    event_type: str,
    payload: dict | None = None,
    sequence_number: int = 1,
) -> MagicMock:
    e = MagicMock(spec=CognitiveEvent)
    e.event_type = event_type
    e.payload = payload or {}
    e.sequence_number = sequence_number
    return e


def _default_engine() -> MetricsEngine:
    return MetricsEngine(RubricConfig())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetricsEngineBasic:
    def test_empty_events_returns_none_scores(self) -> None:
        engine = _default_engine()
        session = _make_session()
        result = engine.compute(session, [])

        assert result.metrics.n1_comprehension_score is None
        assert result.metrics.n2_strategy_score is None
        assert result.metrics.n3_validation_score is None
        assert result.metrics.n4_ai_interaction_score is None
        assert result.metrics.total_interactions == 0
        assert result.metrics.help_seeking_ratio is None
        assert result.metrics.autonomy_index is None

    def test_compute_result_has_all_required_keys(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        result = engine.compute(session, events)

        profile = result.evaluation_profile
        assert "n1" in profile
        assert "n2" in profile
        assert "n3" in profile
        assert "n4" in profile
        assert "qe" in profile
        assert "weighted_total" in profile
        assert "weights" in profile
        assert "risk_level" in profile
        assert "computed_at" in profile

    def test_total_interactions_counted(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.snapshot", sequence_number=2),
            _make_event("code.run", sequence_number=3),
        ]
        result = engine.compute(session, events)
        assert result.metrics.total_interactions == 3


class TestN1Score:
    def test_all_n1_events_gives_max_score(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("reads_problem", sequence_number=2),
            _make_event("code.snapshot", sequence_number=3),
            _make_event("code.snapshot", sequence_number=4),
        ]
        result = engine.compute(session, events)
        # 4/4 N1 events = 100
        assert result.metrics.n1_comprehension_score == Decimal("100.00")

    def test_half_n1_events_gives_50(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.run", sequence_number=2),  # N3, not N1
        ]
        result = engine.compute(session, events)
        # 1/2 = 50
        assert result.metrics.n1_comprehension_score == Decimal("50.00")

    def test_no_n1_events_gives_zero(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", sequence_number=1),
            _make_event("code.run", sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.n1_comprehension_score == Decimal("0.00")

    def test_n1_score_clamped_to_100(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=i + 1) for i in range(10)]
        result = engine.compute(session, events)
        assert result.metrics.n1_comprehension_score == Decimal("100.00")


class TestN2Score:
    def test_submission_with_prior_run_gives_quality_bonus(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", sequence_number=1),
            _make_event("submission.created", sequence_number=2),
        ]
        result = engine.compute(session, events)
        # N2 events: 1 submission. With prior run: quality_factor = 1.0
        # (1/2) * 1.0 * 100 = 50.00
        assert result.metrics.n2_strategy_score == Decimal("50.00")

    def test_submission_without_prior_run_penalized(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("submission.created", sequence_number=2),
        ]
        result = engine.compute(session, events)
        # (1/2) * 0.5 * 100 = 25.00
        assert result.metrics.n2_strategy_score == Decimal("25.00")

    def test_no_submission_gives_zero(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        result = engine.compute(session, events)
        assert result.metrics.n2_strategy_score == Decimal("0.00")


class TestN3Score:
    def test_single_run_gives_base_score(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.run", sequence_number=2),
        ]
        result = engine.compute(session, events)
        # quality_factor = 1.0 for single run
        # (1/2) * 1.0 * 100 = 50.00
        assert result.metrics.n3_validation_score == Decimal("50.00")

    def test_multiple_runs_get_quality_boost(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("code.run", sequence_number=1),
            _make_event("code.run", sequence_number=2),
            _make_event("code.run", sequence_number=3),
        ]
        result = engine.compute(session, events)
        # quality_factor = 1.2 for >= 3 runs
        # (3/3) * 1.2 * 100 = 120.00, clamped to 100.00
        assert result.metrics.n3_validation_score == Decimal("100.00")

    def test_no_run_events_gives_zero(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("submission.created", sequence_number=1)]
        result = engine.compute(session, events)
        assert result.metrics.n3_validation_score == Decimal("0.00")


class TestRatios:
    def test_help_seeking_ratio_and_autonomy_index_sum_to_one(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("tutor.question_asked", {"n4_level": 2}, sequence_number=2),
        ]
        result = engine.compute(session, events)
        hsr = result.metrics.help_seeking_ratio
        ai = result.metrics.autonomy_index
        assert hsr is not None
        assert ai is not None
        total = float(hsr) + float(ai)
        assert abs(total - 1.0) < 0.001

    def test_zero_tutor_events_gives_zero_help_seeking(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.run", sequence_number=2),
        ]
        result = engine.compute(session, events)
        assert result.metrics.help_seeking_ratio == Decimal("0.000")
        assert result.metrics.autonomy_index == Decimal("1.000")


class TestDependencyScore:
    def test_all_dependent_gives_one(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event(
                "tutor.question_asked",
                {"n4_level": 1, "sub_classification": "dependent"},
                sequence_number=1,
            ),
            _make_event(
                "tutor.question_asked",
                {"n4_level": 1, "sub_classification": "dependent"},
                sequence_number=2,
            ),
        ]
        result = engine.compute(session, events)
        assert result.metrics.dependency_score == Decimal("1.000")

    def test_no_dependent_gives_zero(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event(
                "tutor.question_asked",
                {"n4_level": 3, "sub_classification": "autonomous"},
                sequence_number=1,
            ),
        ]
        result = engine.compute(session, events)
        assert result.metrics.dependency_score == Decimal("0.000")

    def test_half_dependent(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event(
                "tutor.question_asked",
                {"n4_level": 1, "sub_classification": "dependent"},
                sequence_number=1,
            ),
            _make_event(
                "tutor.question_asked",
                {"n4_level": 3, "sub_classification": "autonomous"},
                sequence_number=2,
            ),
        ]
        result = engine.compute(session, events)
        assert result.metrics.dependency_score == Decimal("0.500")


class TestWeightedTotal:
    def test_weighted_total_within_range(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [
            _make_event("reads_problem", sequence_number=1),
            _make_event("code.run", sequence_number=2),
            _make_event("submission.created", sequence_number=3),
            _make_event(
                "tutor.question_asked",
                {"n4_level": 2, "sub_classification": "autonomous"},
                sequence_number=4,
            ),
        ]
        result = engine.compute(session, events)
        wt = result.evaluation_profile["weighted_total"]
        assert 0.0 <= wt <= 100.0

    def test_evaluation_profile_weights_match_rubric(self) -> None:
        rubric = RubricConfig()
        engine = MetricsEngine(rubric)
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        result = engine.compute(session, events)

        profile_weights = result.evaluation_profile["weights"]
        assert profile_weights["n1"] == rubric.weights.n1_comprehension
        assert profile_weights["n2"] == rubric.weights.n2_strategy
        assert profile_weights["n3"] == rubric.weights.n3_validation
        assert profile_weights["n4"] == rubric.weights.n4_ai_interaction
        assert profile_weights["qe"] == rubric.weights.qe


class TestReasoningRecord:
    def test_create_reasoning_record_has_correct_keys(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        compute_result = engine.compute(session, events)

        from datetime import datetime, timezone

        rr = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="a" * 64,
            created_at=datetime.now(tz=timezone.utc),
        )

        assert rr["record_type"] == "metrics_computation"
        assert len(rr["event_hash"]) == 64
        assert rr["previous_hash"] == "a" * 64
        assert "session_id" in rr
        assert "details" in rr
        assert "created_at" in rr

    def test_reasoning_record_hash_deterministic(self) -> None:
        engine = _default_engine()
        session = _make_session()
        events = [_make_event("reads_problem", sequence_number=1)]
        compute_result = engine.compute(session, events)

        from datetime import datetime, timezone

        now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        rr1 = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="b" * 64,
            created_at=now,
        )
        rr2 = engine.create_reasoning_record(
            session_id=session.id,
            details=compute_result.reasoning_details,
            previous_hash="b" * 64,
            created_at=now,
        )
        assert rr1["event_hash"] == rr2["event_hash"]
