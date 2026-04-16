"""Risk Assessment router — thin layer, all logic in RiskWorker service.

4 endpoints:
  GET  /api/v1/teacher/commissions/{id}/risks          — list risks by commission
  GET  /api/v1/teacher/students/{id}/risks              — student risk history
  PATCH /api/v1/teacher/risks/{id}/acknowledge          — acknowledge a risk
  POST /api/v1/teacher/commissions/{id}/risks/assess    — trigger manual assessment
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.features.auth.dependencies import require_role
from app.features.evaluation.repositories import CognitiveMetricsRepository
from app.features.risk.models import RiskAssessment
from app.features.risk.repositories import RiskAssessmentRepository
from app.features.risk.schemas import (
    AssessCommissionResponse,
    MetaBlock,
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
    RiskAssessmentStandardResponse,
)
from app.features.risk.service import RiskWorker
from app.shared.db.session import get_async_session
from app.shared.models.user import User

logger = get_logger(__name__)

router = APIRouter(tags=["risk"])


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def _get_risk_repo(
    session: AsyncSession = Depends(get_async_session),
) -> RiskAssessmentRepository:
    return RiskAssessmentRepository(session)


def _get_risk_worker(
    session: AsyncSession = Depends(get_async_session),
) -> RiskWorker:
    return RiskWorker(
        metrics_repo=CognitiveMetricsRepository(session),
        risk_repo=RiskAssessmentRepository(session),
        session=session,
    )


def _to_response(ra: RiskAssessment) -> RiskAssessmentResponse:
    return RiskAssessmentResponse(
        id=str(ra.id),
        student_id=str(ra.student_id),
        commission_id=str(ra.commission_id),
        risk_level=ra.risk_level,
        risk_factors=ra.risk_factors,
        recommendation=ra.recommendation,
        triggered_by=ra.triggered_by,
        assessed_at=ra.assessed_at,
        acknowledged_by=str(ra.acknowledged_by) if ra.acknowledged_by else None,
        acknowledged_at=ra.acknowledged_at,
    )


# ---------------------------------------------------------------------------
# 1. GET /api/v1/teacher/commissions/{commission_id}/risks
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/teacher/commissions/{commission_id}/risks",
    response_model=RiskAssessmentListResponse,
    summary="List risk assessments for a commission",
)
async def list_commission_risks(
    commission_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    risk_repo: RiskAssessmentRepository = Depends(_get_risk_repo),
    _user: User = require_role("docente", "admin"),
) -> RiskAssessmentListResponse:
    items, total = await risk_repo.get_by_commission(
        commission_id=commission_id,
        page=page,
        per_page=per_page,
        risk_level=risk_level,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    return RiskAssessmentListResponse(
        status="ok",
        data=[_to_response(r) for r in items],
        meta=MetaBlock(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


# ---------------------------------------------------------------------------
# 2. GET /api/v1/teacher/students/{student_id}/risks
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/teacher/students/{student_id}/risks",
    response_model=RiskAssessmentListResponse,
    summary="Student risk assessment history",
)
async def list_student_risks(
    student_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    commission_id: uuid.UUID | None = Query(None, description="Filter by commission"),
    risk_repo: RiskAssessmentRepository = Depends(_get_risk_repo),
    _user: User = require_role("docente", "admin"),
) -> RiskAssessmentListResponse:
    items, total = await risk_repo.get_by_student(
        student_id=student_id,
        page=page,
        per_page=per_page,
        commission_id=commission_id,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    return RiskAssessmentListResponse(
        status="ok",
        data=[_to_response(r) for r in items],
        meta=MetaBlock(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


# ---------------------------------------------------------------------------
# 3. PATCH /api/v1/teacher/risks/{risk_id}/acknowledge
# ---------------------------------------------------------------------------


@router.patch(
    "/api/v1/teacher/risks/{risk_id}/acknowledge",
    response_model=RiskAssessmentStandardResponse,
    summary="Acknowledge a risk assessment",
)
async def acknowledge_risk(
    risk_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = require_role("docente", "admin"),
) -> RiskAssessmentStandardResponse:
    risk_repo = RiskAssessmentRepository(db)
    try:
        ra = await risk_repo.get_by_id(risk_id)
    except NotFoundError:
        raise NotFoundError(resource="RiskAssessment", identifier=str(risk_id))

    ra.acknowledged_by = current_user.id
    ra.acknowledged_at = datetime.now(tz=timezone.utc)
    await db.commit()

    return RiskAssessmentStandardResponse(
        status="ok",
        data=_to_response(ra),
    )


# ---------------------------------------------------------------------------
# 4. POST /api/v1/teacher/commissions/{commission_id}/risks/assess
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/teacher/commissions/{commission_id}/risks/assess",
    response_model=AssessCommissionResponse,
    summary="Trigger manual risk assessment for a commission",
)
async def trigger_commission_assessment(
    commission_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _user: User = require_role("docente", "admin"),
) -> AssessCommissionResponse:
    worker = RiskWorker(
        metrics_repo=CognitiveMetricsRepository(db),
        risk_repo=RiskAssessmentRepository(db),
        session=db,
    )
    count = await worker.assess_commission(commission_id, triggered_by="manual")
    await db.commit()

    return AssessCommissionResponse(
        status="ok",
        data={"assessed_count": count},
    )
