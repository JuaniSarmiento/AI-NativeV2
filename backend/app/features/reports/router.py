from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import require_role
from app.features.reports.schemas import (
    GenerateReportRequest,
    ReportResponse,
    ReportStandardResponse,
)
from app.features.reports.service import ReportService
from app.shared.db.session import get_async_session
from app.shared.models.user import User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def get_report_service(
    session: AsyncSession = Depends(get_async_session),
) -> ReportService:
    return ReportService(session)


@router.post(
    "/generate",
    response_model=ReportStandardResponse,
    summary="Generate cognitive report for student+activity",
)
async def generate_report(
    body: GenerateReportRequest,
    service: ReportService = Depends(get_report_service),
    db: AsyncSession = Depends(get_async_session),
    user: User = require_role("docente", "admin"),
) -> ReportStandardResponse:
    report = await service.generate_report(
        student_id=body.student_id,
        activity_id=body.activity_id,
        commission_id=body.commission_id,
        requested_by=user.id,
    )
    await db.commit()
    return ReportStandardResponse(data=ReportResponse.from_orm(report))


@router.get(
    "/{report_id}",
    response_model=ReportStandardResponse,
    summary="Get a generated report by ID",
)
async def get_report(
    report_id: uuid.UUID,
    service: ReportService = Depends(get_report_service),
    _user: User = require_role("docente", "admin"),
) -> ReportStandardResponse:
    report = await service.get_report(report_id)
    return ReportStandardResponse(data=ReportResponse.from_orm(report))


@router.get(
    "",
    response_model=ReportStandardResponse,
    summary="Get latest report for student+activity",
)
async def get_latest_report(
    student_id: uuid.UUID = Query(...),
    activity_id: uuid.UUID = Query(...),
    service: ReportService = Depends(get_report_service),
    _user: User = require_role("docente", "admin"),
) -> ReportStandardResponse:
    report = await service.get_latest_report(student_id, activity_id)
    if report is None:
        return ReportStandardResponse(data=None)
    return ReportStandardResponse(data=ReportResponse.from_orm(report))
