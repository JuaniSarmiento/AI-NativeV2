"""Unit tests for risk router endpoints.

Tests the HTTP layer in isolation using mocked dependencies.
Follows the pattern from other router tests in the project.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.risk.models import RiskAssessment
from app.features.risk.router import (
    _to_response,
    acknowledge_risk,
    list_commission_risks,
    list_student_risks,
    trigger_commission_assessment,
)
from app.core.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_risk_assessment(**overrides) -> MagicMock:
    ra = MagicMock(spec=RiskAssessment)
    ra.id = overrides.get("id", uuid.uuid4())
    ra.student_id = overrides.get("student_id", uuid.uuid4())
    ra.commission_id = overrides.get("commission_id", uuid.uuid4())
    ra.risk_level = overrides.get("risk_level", "high")
    ra.risk_factors = overrides.get("risk_factors", {"dependency": {"score": 0.7}})
    ra.recommendation = overrides.get("recommendation", "Fomentar autonomia")
    ra.triggered_by = overrides.get("triggered_by", "automatic")
    ra.assessed_at = overrides.get("assessed_at", datetime.now(tz=timezone.utc))
    ra.acknowledged_by = overrides.get("acknowledged_by", None)
    ra.acknowledged_at = overrides.get("acknowledged_at", None)
    return ra


def _mock_user(role: str = "docente") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.role = role
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestToResponse:
    def test_converts_orm_to_dto(self) -> None:
        ra = _make_risk_assessment()
        resp = _to_response(ra)
        assert resp.id == str(ra.id)
        assert resp.student_id == str(ra.student_id)
        assert resp.risk_level == "high"
        assert resp.acknowledged_by is None


class TestListCommissionRisks:
    @pytest.mark.asyncio
    async def test_returns_paginated_list(self) -> None:
        commission_id = uuid.uuid4()
        ra1 = _make_risk_assessment(commission_id=commission_id)
        ra2 = _make_risk_assessment(commission_id=commission_id)

        repo = MagicMock()
        repo.get_by_commission = AsyncMock(return_value=([ra1, ra2], 2))

        result = await list_commission_risks(
            commission_id=commission_id,
            page=1,
            per_page=20,
            risk_level=None,
            risk_repo=repo,
            _user=_mock_user(),
        )

        assert result.status == "ok"
        assert len(result.data) == 2
        assert result.meta.total == 2

    @pytest.mark.asyncio
    async def test_filters_by_risk_level(self) -> None:
        commission_id = uuid.uuid4()
        repo = MagicMock()
        repo.get_by_commission = AsyncMock(return_value=([], 0))

        await list_commission_risks(
            commission_id=commission_id,
            page=1,
            per_page=20,
            risk_level="critical",
            risk_repo=repo,
            _user=_mock_user(),
        )

        repo.get_by_commission.assert_called_once_with(
            commission_id=commission_id,
            page=1,
            per_page=20,
            risk_level="critical",
        )


class TestListStudentRisks:
    @pytest.mark.asyncio
    async def test_returns_student_history(self) -> None:
        student_id = uuid.uuid4()
        ra = _make_risk_assessment(student_id=student_id)

        repo = MagicMock()
        repo.get_by_student = AsyncMock(return_value=([ra], 1))

        result = await list_student_risks(
            student_id=student_id,
            page=1,
            per_page=20,
            commission_id=None,
            risk_repo=repo,
            _user=_mock_user(),
        )

        assert result.status == "ok"
        assert len(result.data) == 1


class TestAcknowledgeRisk:
    @pytest.mark.asyncio
    async def test_sets_acknowledged_fields(self) -> None:
        risk_id = uuid.uuid4()
        ra = _make_risk_assessment(id=risk_id)
        ra.acknowledged_by = None
        ra.acknowledged_at = None

        db = MagicMock()
        db.commit = AsyncMock()

        user = _mock_user()

        with patch(
            "app.features.risk.router.RiskAssessmentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=ra)

            result = await acknowledge_risk(
                risk_id=risk_id,
                db=db,
                current_user=user,
            )

        assert ra.acknowledged_by == user.id
        assert ra.acknowledged_at is not None
        assert result.status == "ok"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = MagicMock()
        db.commit = AsyncMock()

        with patch(
            "app.features.risk.router.RiskAssessmentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(
                side_effect=NotFoundError(resource="RiskAssessment", identifier="xxx")
            )

            with pytest.raises(NotFoundError):
                await acknowledge_risk(
                    risk_id=uuid.uuid4(),
                    db=db,
                    current_user=_mock_user(),
                )


class TestTriggerAssessment:
    @pytest.mark.asyncio
    async def test_returns_assessed_count(self) -> None:
        commission_id = uuid.uuid4()
        db = MagicMock()
        db.commit = AsyncMock()

        with patch("app.features.risk.router.RiskWorker") as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.assess_commission = AsyncMock(return_value=5)

            result = await trigger_commission_assessment(
                commission_id=commission_id,
                db=db,
                _user=_mock_user(),
            )

        assert result.status == "ok"
        assert result.data == {"assessed_count": 5}
        mock_worker.assess_commission.assert_called_once_with(
            commission_id, triggered_by="manual"
        )
        db.commit.assert_called_once()
