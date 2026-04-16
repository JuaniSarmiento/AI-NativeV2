"""Evaluation / Cognitive Metrics router.

4 endpoints:
  GET /api/v1/cognitive/sessions/{id}/metrics     — docente / admin
  GET /api/v1/teacher/courses/{id}/dashboard      — docente / admin
  GET /api/v1/teacher/students/{id}/profile       — docente / admin
  GET /api/v1/student/me/progress                 — alumno

Routers are THIN: validate input → call repo/service → return response.
All business logic lives in repositories or the MetricsEngine service.

Auth pattern: require_role() as a SEPARATE Depends param, NOT a default
on CurrentUser, following the convention established in the cognitive router.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.cognitive.models import CognitiveSession
from app.features.evaluation.repositories import CognitiveMetricsRepository
from app.features.evaluation.schemas import (
    CognitiveMetricsResponse,
    DashboardResponse,
    DashboardStandardResponse,
    MetaBlock,
    MetricsStandardResponse,
    StudentProfileResponse,
    StudentProfileStandardResponse,
    StudentProgressItem,
    StudentProgressResponse,
    StudentProgressStandardResponse,
    StudentSummary,
)
from app.shared.db.session import get_async_session
from app.shared.models.user import User

logger = get_logger(__name__)

router = APIRouter(tags=["evaluation"])


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------


def get_metrics_repo(
    session: AsyncSession = Depends(get_async_session),
) -> CognitiveMetricsRepository:
    return CognitiveMetricsRepository(session)


# ---------------------------------------------------------------------------
# 1. GET /api/v1/cognitive/sessions/{session_id}/metrics
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/cognitive/sessions/{session_id}/metrics",
    response_model=MetricsStandardResponse,
    summary="Get computed cognitive metrics for a session",
    description=(
        "Returns the N1-N4 scores, Qe sub-scores, dependency score, and risk "
        "classification for a specific cognitive session. Requires role docente or admin."
    ),
)
async def get_session_metrics(
    session_id: uuid.UUID,
    metrics_repo: CognitiveMetricsRepository = Depends(get_metrics_repo),
    _user: User = require_role("docente", "admin"),
) -> MetricsStandardResponse:
    metrics = await metrics_repo.get_by_session(session_id)
    if metrics is None:
        raise NotFoundError(resource="CognitiveMetrics", identifier=str(session_id))

    return MetricsStandardResponse(
        status="ok",
        data=CognitiveMetricsResponse.from_orm(metrics),
    )


# ---------------------------------------------------------------------------
# 2. GET /api/v1/teacher/courses/{course_id}/dashboard
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/teacher/courses/{course_id}/dashboard",
    response_model=DashboardStandardResponse,
    summary="Commission-level cognitive dashboard",
    description=(
        "Returns aggregated N1-N4 averages, risk distribution, and per-student "
        "summaries for a commission (optionally filtered by exercise). "
        "Requires role docente or admin."
    ),
)
async def get_commission_dashboard(
    course_id: uuid.UUID,
    commission_id: uuid.UUID = Query(..., description="Commission UUID to scope the dashboard"),
    exercise_id: uuid.UUID | None = Query(None, description="Optional exercise filter"),
    db: AsyncSession = Depends(get_async_session),
    _user: User = require_role("docente", "admin"),
) -> DashboardStandardResponse:
    from sqlalchemy import select, func as sa_func
    from app.features.evaluation.models import CognitiveMetrics

    metrics_repo = CognitiveMetricsRepository(db)
    aggregates = await metrics_repo.get_commission_aggregates(commission_id, exercise_id)

    # Fetch per-student summaries
    stmt = (
        select(
            CognitiveSession.student_id,
            sa_func.count(CognitiveSession.id).label("session_count"),
        )
        .where(CognitiveSession.commission_id == commission_id)
        .group_by(CognitiveSession.student_id)
    )
    if exercise_id is not None:
        stmt = stmt.where(CognitiveSession.exercise_id == exercise_id)

    student_rows = (await db.execute(stmt)).all()

    student_summaries: list[StudentSummary] = []
    for row in student_rows:
        # Get most recent metrics for this student in this commission/exercise scope
        student_metrics, _ = await metrics_repo.get_by_student(
            student_id=row.student_id, page=1, per_page=1
        )
        latest = student_metrics[0] if student_metrics else None

        def _f(v: Any) -> float | None:
            return float(v) if v is not None else None

        student_summaries.append(
            StudentSummary(
                student_id=str(row.student_id),
                session_count=row.session_count,
                latest_n1=_f(getattr(latest, "n1_comprehension_score", None)) if latest else None,
                latest_n2=_f(getattr(latest, "n2_strategy_score", None)) if latest else None,
                latest_n3=_f(getattr(latest, "n3_validation_score", None)) if latest else None,
                latest_n4=_f(getattr(latest, "n4_ai_interaction_score", None)) if latest else None,
                latest_qe=_f(getattr(latest, "qe_score", None)) if latest else None,
                latest_risk_level=getattr(latest, "risk_level", None) if latest else None,
                avg_dependency=_f(getattr(latest, "dependency_score", None)) if latest else None,
            )
        )

    dashboard = DashboardResponse(
        commission_id=str(commission_id),
        exercise_id=str(exercise_id) if exercise_id else None,
        student_count=aggregates["student_count"],
        avg_n1=aggregates["avg_n1"],
        avg_n2=aggregates["avg_n2"],
        avg_n3=aggregates["avg_n3"],
        avg_n4=aggregates["avg_n4"],
        avg_qe=aggregates["avg_qe"],
        avg_dependency=aggregates["avg_dependency"],
        risk_distribution=aggregates["risk_distribution"],
        students=student_summaries,
    )

    return DashboardStandardResponse(status="ok", data=dashboard)


# ---------------------------------------------------------------------------
# 3. GET /api/v1/teacher/students/{student_id}/profile
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/teacher/students/{student_id}/profile",
    response_model=StudentProfileStandardResponse,
    summary="Detailed cognitive profile for a specific student",
    description=(
        "Returns the full list of CognitiveMetrics records for a student, "
        "paginated. Includes risk level, dependency scores, and all N1-N4 scores. "
        "Requires role docente or admin."
    ),
)
async def get_student_profile(
    student_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    metrics_repo: CognitiveMetricsRepository = Depends(get_metrics_repo),
    _user: User = require_role("docente", "admin"),
) -> StudentProfileStandardResponse:
    items, total = await metrics_repo.get_by_student(
        student_id=student_id, page=page, per_page=per_page
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    return StudentProfileStandardResponse(
        status="ok",
        data=StudentProfileResponse(
            student_id=str(student_id),
            metrics=[CognitiveMetricsResponse.from_orm(m) for m in items],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        ),
        meta=MetaBlock(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


# ---------------------------------------------------------------------------
# 4. GET /api/v1/student/me/progress
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/student/me/progress",
    response_model=StudentProgressStandardResponse,
    summary="Student's own cognitive progress",
    description=(
        "Returns the authenticated student's N1-N4 scores and Qe across all "
        "their sessions. Anti-gaming: dependency_score, risk_level, and "
        "help_seeking_ratio are intentionally excluded. Requires role alumno."
    ),
)
async def get_my_progress(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = require_role("alumno"),
) -> StudentProgressStandardResponse:
    from sqlalchemy import select, func as sa_func
    from app.features.evaluation.models import CognitiveMetrics

    metrics_repo = CognitiveMetricsRepository(db)
    items, total = await metrics_repo.get_by_student(
        student_id=current_user.id, page=page, per_page=per_page
    )

    # For each metrics row, also fetch the corresponding session to get exercise_id
    session_ids = [m.session_id for m in items]
    session_map: dict[Any, Any] = {}
    if session_ids:
        sess_stmt = select(CognitiveSession).where(CognitiveSession.id.in_(session_ids))
        sess_rows = (await db.execute(sess_stmt)).scalars().all()
        session_map = {s.id: s for s in sess_rows}

    def _f(v: Any) -> float | None:
        return float(v) if v is not None else None

    progress_items = [
        StudentProgressItem(
            session_id=str(m.session_id),
            exercise_id=str(session_map[m.session_id].exercise_id)
            if m.session_id in session_map
            else "",
            n1_comprehension_score=_f(m.n1_comprehension_score),
            n2_strategy_score=_f(m.n2_strategy_score),
            n3_validation_score=_f(m.n3_validation_score),
            n4_ai_interaction_score=_f(m.n4_ai_interaction_score),
            qe_score=_f(m.qe_score),
            autonomy_index=_f(m.autonomy_index),
            success_efficiency=_f(m.success_efficiency),
            computed_at=m.computed_at,
        )
        for m in items
    ]

    # Compute averages across the whole student (not just this page)
    avg_stmt = (
        select(
            sa_func.avg(CognitiveMetrics.n1_comprehension_score).label("avg_n1"),
            sa_func.avg(CognitiveMetrics.n2_strategy_score).label("avg_n2"),
            sa_func.avg(CognitiveMetrics.n3_validation_score).label("avg_n3"),
            sa_func.avg(CognitiveMetrics.n4_ai_interaction_score).label("avg_n4"),
            sa_func.avg(CognitiveMetrics.qe_score).label("avg_qe"),
        )
        .select_from(
            CognitiveMetrics.__table__.join(
                CognitiveSession.__table__,
                CognitiveMetrics.__table__.c.session_id == CognitiveSession.__table__.c.id,
            )
        )
        .where(CognitiveSession.student_id == current_user.id)
    )
    avg_row = (await db.execute(avg_stmt)).one_or_none()

    return StudentProgressStandardResponse(
        status="ok",
        data=StudentProgressResponse(
            sessions=progress_items,
            session_count=total,
            avg_n1=_f(avg_row.avg_n1) if avg_row else None,
            avg_n2=_f(avg_row.avg_n2) if avg_row else None,
            avg_n3=_f(avg_row.avg_n3) if avg_row else None,
            avg_n4=_f(avg_row.avg_n4) if avg_row else None,
            avg_qe=_f(avg_row.avg_qe) if avg_row else None,
        ),
        meta={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    )
