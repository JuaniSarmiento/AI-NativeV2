"""Unit tests for RiskAssessmentRepository.

Uses MagicMock for AsyncSession to test query construction
without a real database. Follows the same pattern as other
repository tests in the project.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.risk.models import RiskAssessment
from app.features.risk.repositories import RiskAssessmentRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_risk_assessment(**overrides) -> MagicMock:
    ra = MagicMock(spec=RiskAssessment)
    ra.id = overrides.get("id", uuid.uuid4())
    ra.student_id = overrides.get("student_id", uuid.uuid4())
    ra.commission_id = overrides.get("commission_id", uuid.uuid4())
    ra.risk_level = overrides.get("risk_level", "medium")
    ra.risk_factors = overrides.get("risk_factors", {"dependency": {"score": 0.6}})
    ra.recommendation = overrides.get("recommendation", "Test recommendation")
    ra.triggered_by = overrides.get("triggered_by", "automatic")
    ra.assessed_at = overrides.get("assessed_at", datetime.now(tz=timezone.utc))
    ra.acknowledged_by = overrides.get("acknowledged_by", None)
    ra.acknowledged_at = overrides.get("acknowledged_at", None)
    return ra


def _mock_session() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRiskAssessmentRepositoryInit:
    def test_creates_with_session(self) -> None:
        session = _mock_session()
        repo = RiskAssessmentRepository(session)
        assert repo._session is session
        assert repo._model_class is RiskAssessment


class TestGetByCommission:
    @pytest.mark.asyncio
    async def test_calls_execute_with_commission_filter(self) -> None:
        session = _mock_session()
        commission_id = uuid.uuid4()

        # Mock scalar_one for count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        # Mock scalars().all() for items
        items_result = MagicMock()
        ra1 = _make_risk_assessment(commission_id=commission_id)
        ra2 = _make_risk_assessment(commission_id=commission_id)
        items_result.scalars.return_value.all.return_value = [ra1, ra2]

        session.execute = AsyncMock(side_effect=[count_result, items_result])

        repo = RiskAssessmentRepository(session)
        items, total = await repo.get_by_commission(commission_id)

        assert total == 2
        assert len(items) == 2
        assert session.execute.call_count == 2


class TestGetByStudent:
    @pytest.mark.asyncio
    async def test_calls_execute_with_student_filter(self) -> None:
        session = _mock_session()
        student_id = uuid.uuid4()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        items_result = MagicMock()
        ra = _make_risk_assessment(student_id=student_id)
        items_result.scalars.return_value.all.return_value = [ra]

        session.execute = AsyncMock(side_effect=[count_result, items_result])

        repo = RiskAssessmentRepository(session)
        items, total = await repo.get_by_student(student_id)

        assert total == 1
        assert len(items) == 1


class TestGetActiveByStudentCommission:
    @pytest.mark.asyncio
    async def test_returns_most_recent_unacknowledged(self) -> None:
        session = _mock_session()
        student_id = uuid.uuid4()
        commission_id = uuid.uuid4()

        ra = _make_risk_assessment(
            student_id=student_id,
            commission_id=commission_id,
        )

        result = MagicMock()
        result.scalar_one_or_none.return_value = ra
        session.execute = AsyncMock(return_value=result)

        repo = RiskAssessmentRepository(session)
        active = await repo.get_active_by_student_commission(student_id, commission_id)

        assert active is ra

    @pytest.mark.asyncio
    async def test_returns_none_when_all_acknowledged(self) -> None:
        session = _mock_session()

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        repo = RiskAssessmentRepository(session)
        active = await repo.get_active_by_student_commission(uuid.uuid4(), uuid.uuid4())

        assert active is None
