"""Unit tests for RiskWorker — factor detection, risk level, recommendations.

Uses MagicMock to avoid database dependencies. RiskWorker's factor detection
methods are tested directly since they are pure computation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.features.cognitive.models import CognitiveSession
from app.features.evaluation.models import CognitiveMetrics
from app.features.risk.service import RiskWorker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metrics(
    dependency_score: float | None = None,
    n1: float | None = 50.0,
    n2: float | None = 50.0,
    n3: float | None = 50.0,
    n4: float | None = 50.0,
    computed_at: datetime | None = None,
) -> MagicMock:
    m = MagicMock(spec=CognitiveMetrics)
    m.dependency_score = Decimal(str(dependency_score)) if dependency_score is not None else None
    m.n1_comprehension_score = Decimal(str(n1)) if n1 is not None else None
    m.n2_strategy_score = Decimal(str(n2)) if n2 is not None else None
    m.n3_validation_score = Decimal(str(n3)) if n3 is not None else None
    m.n4_ai_interaction_score = Decimal(str(n4)) if n4 is not None else None
    m.computed_at = computed_at or datetime.now(tz=timezone.utc)
    return m


def _make_session(started_at: datetime | None = None) -> MagicMock:
    s = MagicMock(spec=CognitiveSession)
    s.id = uuid.uuid4()
    s.student_id = uuid.uuid4()
    s.started_at = started_at or datetime.now(tz=timezone.utc)
    return s


def _make_worker() -> RiskWorker:
    return RiskWorker(
        metrics_repo=MagicMock(),
        risk_repo=MagicMock(),
        session=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Dependency factor
# ---------------------------------------------------------------------------


class TestDependencyFactor:
    def test_high_dependency_detected(self) -> None:
        worker = _make_worker()
        metrics = [_make_metrics(dependency_score=0.7) for _ in range(5)]
        result = worker._detect_dependency_factor(metrics)
        assert result is not None
        assert result["score"] == 0.7
        assert result["sessions_above_threshold"] == 5

    def test_low_dependency_not_detected(self) -> None:
        worker = _make_worker()
        metrics = [_make_metrics(dependency_score=0.3) for _ in range(5)]
        result = worker._detect_dependency_factor(metrics)
        assert result is None

    def test_mixed_dependency(self) -> None:
        worker = _make_worker()
        # avg = (0.7 + 0.7 + 0.3 + 0.3 + 0.6) / 5 = 0.52 > 0.5
        metrics = [
            _make_metrics(dependency_score=0.7),
            _make_metrics(dependency_score=0.7),
            _make_metrics(dependency_score=0.3),
            _make_metrics(dependency_score=0.3),
            _make_metrics(dependency_score=0.6),
        ]
        result = worker._detect_dependency_factor(metrics)
        assert result is not None
        assert result["score"] == 0.52

    def test_no_metrics_returns_none(self) -> None:
        worker = _make_worker()
        assert worker._detect_dependency_factor([]) is None

    def test_null_dependency_scores(self) -> None:
        worker = _make_worker()
        metrics = [_make_metrics(dependency_score=None) for _ in range(3)]
        assert worker._detect_dependency_factor(metrics) is None


# ---------------------------------------------------------------------------
# Disengagement factor
# ---------------------------------------------------------------------------


class TestDisengagementFactor:
    def test_no_recent_sessions(self) -> None:
        worker = _make_worker()
        old = datetime.now(tz=timezone.utc) - timedelta(days=14)
        sessions = [_make_session(started_at=old) for _ in range(3)]
        result = worker._detect_disengagement_factor(sessions)
        assert result is not None
        assert result["score"] == 1.0
        assert result["recent_sessions"] == 0

    def test_one_recent_session(self) -> None:
        worker = _make_worker()
        recent = datetime.now(tz=timezone.utc) - timedelta(days=2)
        old = datetime.now(tz=timezone.utc) - timedelta(days=14)
        sessions = [_make_session(started_at=recent), _make_session(started_at=old)]
        result = worker._detect_disengagement_factor(sessions)
        assert result is not None
        assert result["score"] == 0.5
        assert result["recent_sessions"] == 1

    def test_active_student_no_disengagement(self) -> None:
        worker = _make_worker()
        recent = datetime.now(tz=timezone.utc) - timedelta(days=1)
        sessions = [_make_session(started_at=recent) for _ in range(3)]
        result = worker._detect_disengagement_factor(sessions)
        assert result is None


# ---------------------------------------------------------------------------
# Stagnation factor
# ---------------------------------------------------------------------------


class TestStagnationFactor:
    def test_declining_scores(self) -> None:
        worker = _make_worker()
        # newest first — scores declining over time
        metrics = [
            _make_metrics(n1=30, n2=30, n3=30, n4=30),  # newest
            _make_metrics(n1=50, n2=50, n3=50, n4=50),
            _make_metrics(n1=70, n2=70, n3=70, n4=70),  # oldest
        ]
        result = worker._detect_stagnation_factor(metrics)
        assert result is not None
        assert result["trend"] == "declining"
        assert result["score"] > 0

    def test_improving_scores(self) -> None:
        worker = _make_worker()
        # newest first — scores improving over time
        metrics = [
            _make_metrics(n1=70, n2=70, n3=70, n4=70),  # newest
            _make_metrics(n1=50, n2=50, n3=50, n4=50),
            _make_metrics(n1=30, n2=30, n3=30, n4=30),  # oldest
        ]
        result = worker._detect_stagnation_factor(metrics)
        assert result is None

    def test_insufficient_sessions(self) -> None:
        worker = _make_worker()
        metrics = [_make_metrics(), _make_metrics()]
        result = worker._detect_stagnation_factor(metrics)
        assert result is None


# ---------------------------------------------------------------------------
# Risk level computation
# ---------------------------------------------------------------------------


class TestRiskLevel:
    def test_no_factors_is_low(self) -> None:
        assert RiskWorker._compute_risk_level({}) == "low"

    def test_single_critical_factor(self) -> None:
        factors = {"dependency": {"score": 0.85}}
        assert RiskWorker._compute_risk_level(factors) == "critical"

    def test_two_high_factors_is_critical(self) -> None:
        factors = {
            "dependency": {"score": 0.65},
            "disengagement": {"score": 0.7},
        }
        assert RiskWorker._compute_risk_level(factors) == "critical"

    def test_single_high_factor(self) -> None:
        factors = {"dependency": {"score": 0.65}}
        assert RiskWorker._compute_risk_level(factors) == "high"

    def test_medium_factor(self) -> None:
        factors = {"stagnation": {"score": 0.45}}
        assert RiskWorker._compute_risk_level(factors) == "medium"

    def test_low_factor(self) -> None:
        factors = {"stagnation": {"score": 0.2}}
        assert RiskWorker._compute_risk_level(factors) == "low"


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


class TestRecommendation:
    def test_no_factors_returns_none(self) -> None:
        assert RiskWorker._generate_recommendation({}) is None

    def test_dependency_recommendation(self) -> None:
        factors = {"dependency": {"score": 0.7}}
        result = RiskWorker._generate_recommendation(factors)
        assert result is not None
        assert "dependencia" in result.lower()

    def test_multiple_factors(self) -> None:
        factors = {
            "dependency": {"score": 0.7},
            "stagnation": {"score": 0.5},
        }
        result = RiskWorker._generate_recommendation(factors)
        assert result is not None
        assert "dependencia" in result.lower()
        assert "mejora" in result.lower() or "puntajes" in result.lower()
