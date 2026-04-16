from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.auth.dependencies import require_role
from app.features.cognitive.schemas import (
    CodeEvolutionResponse,
    CodeSnapshotEntry,
    CognitiveEventResponse,
    CognitiveSessionDataWrapper,
    CognitiveSessionResponse,
    CognitiveSessionStandardResponse,
    SessionListItem,
    SessionListMeta,
    SessionListResponse,
    TimelineEventResponse,
    TimelineResponse,
    TraceResponse,
    TraceStandardResponse,
    VerifyResponse,
    VerifyStandardResponse,
)
from app.features.cognitive.service import CognitiveService
from app.shared.db.session import get_async_session
from app.shared.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/cognitive", tags=["cognitive"])


def get_cognitive_service(
    session: AsyncSession = Depends(get_async_session),
) -> CognitiveService:
    """Dependency factory — injects CognitiveService with a fresh per-request session."""
    return CognitiveService(session)


@router.get(
    "/sessions/{session_id}",
    response_model=CognitiveSessionStandardResponse,
    summary="Get cognitive session with events",
    description=(
        "Returns the full cognitive session including its hash-chained events. "
        "Access requires role docente or admin."
    ),
)
async def get_cognitive_session(
    session_id: uuid.UUID,
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> CognitiveSessionStandardResponse:
    """Retrieve a cognitive session with all its CTR events eagerly loaded.

    The caller is responsible for DB commit (no mutations happen here).
    """
    cog_session = await service._session_repo.get_session_with_events(session_id)
    if cog_session is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

    return CognitiveSessionStandardResponse(
        status="ok",
        data=CognitiveSessionDataWrapper(
            session=CognitiveSessionResponse.from_orm(cog_session)
        ),
    )


@router.get(
    "/sessions/{session_id}/verify",
    response_model=VerifyStandardResponse,
    summary="Verify CTR hash chain integrity",
    description=(
        "Recalculates all event hashes from genesis_hash forward and reports "
        "whether the chain is intact. Access requires role docente or admin."
    ),
)
async def verify_cognitive_session(
    session_id: uuid.UUID,
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> VerifyStandardResponse:
    """Verify the hash chain of a cognitive session.

    Returns valid=True if all hashes match, or valid=False with the
    sequence number of the first tampered event.
    """
    result = await service.verify_session(session_id)

    return VerifyStandardResponse(
        status="ok",
        data=VerifyResponse(**result),
    )


# ---------------------------------------------------------------------------
# EPIC-16 — Sessions list, Trace, Timeline, Code Evolution
# ---------------------------------------------------------------------------


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List cognitive sessions by commission",
)
async def list_sessions(
    commission_id: uuid.UUID = Query(..., description="Commission UUID (required)"),
    student_id: uuid.UUID | None = Query(None),
    exercise_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="open, closed, or invalidated"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> SessionListResponse:
    items, total = await service._session_repo.get_sessions_by_commission(
        commission_id=commission_id,
        student_id=student_id,
        exercise_id=exercise_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    return SessionListResponse(
        data=[SessionListItem.from_orm(s) for s in items],
        meta=SessionListMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


@router.get(
    "/sessions/{session_id}/trace",
    response_model=TraceStandardResponse,
    summary="Unified cognitive trace for a session",
)
async def get_session_trace(
    session_id: uuid.UUID,
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> TraceStandardResponse:
    from app.core.exceptions import NotFoundError
    from app.features.evaluation.repositories import CognitiveMetricsRepository

    cog_session = await service._session_repo.get_session_with_events(session_id)
    if cog_session is None:
        raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

    # Metrics (may not exist for open sessions)
    metrics_repo = CognitiveMetricsRepository(service._session_repo._session)
    metrics_obj = await metrics_repo.get_by_session(session_id)
    metrics_dict = None
    if metrics_obj is not None:
        from app.features.evaluation.schemas import CognitiveMetricsResponse
        metrics_dict = CognitiveMetricsResponse.from_orm(metrics_obj).model_dump()

    # Verification
    verify_result = None
    if cog_session.status in ("closed", "invalidated"):
        raw = await service.verify_session(session_id)
        verify_result = VerifyResponse(**raw)

    return TraceStandardResponse(
        data=TraceResponse(
            session=CognitiveSessionResponse.from_orm(cog_session),
            metrics=metrics_dict,
            verification=verify_result,
        ),
    )


@router.get(
    "/sessions/{session_id}/timeline",
    response_model=TimelineResponse,
    summary="Paginated timeline of CTR events",
)
async def get_session_timeline(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> TimelineResponse:
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select, func as sa_func
    from app.features.cognitive.models import CognitiveEvent, CognitiveSession

    db = service._session_repo._session

    # Verify session exists
    session_check = await db.execute(
        select(CognitiveSession.id).where(CognitiveSession.id == session_id)
    )
    if session_check.scalar_one_or_none() is None:
        raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

    # Count
    count_stmt = select(sa_func.count()).where(CognitiveEvent.session_id == session_id)
    total: int = (await db.execute(count_stmt)).scalar_one()
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Paginated events
    stmt = (
        select(CognitiveEvent)
        .where(CognitiveEvent.session_id == session_id)
        .order_by(CognitiveEvent.sequence_number)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    events = list(result.scalars().all())

    return TimelineResponse(
        data=[TimelineEventResponse.from_orm(e) for e in events],
        meta=SessionListMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    )


@router.get(
    "/sessions/{session_id}/code-evolution",
    response_model=CodeEvolutionResponse,
    summary="Code snapshots for a session with evolution",
)
async def get_code_evolution(
    session_id: uuid.UUID,
    service: CognitiveService = Depends(get_cognitive_service),
    _user: User = require_role("docente", "admin"),
) -> CodeEvolutionResponse:
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select
    from app.features.cognitive.models import CognitiveEvent, CognitiveSession
    from app.features.submissions.models import CodeSnapshot

    db = service._session_repo._session

    # Verify session exists
    session_check = await db.execute(
        select(CognitiveSession.id).where(CognitiveSession.id == session_id)
    )
    if session_check.scalar_one_or_none() is None:
        raise NotFoundError(resource="CognitiveSession", identifier=str(session_id))

    # Get code.snapshot events for this session
    stmt = (
        select(CognitiveEvent)
        .where(
            CognitiveEvent.session_id == session_id,
            CognitiveEvent.event_type == "code.snapshot",
        )
        .order_by(CognitiveEvent.sequence_number)
    )
    result = await db.execute(stmt)
    snapshot_events = list(result.scalars().all())

    if not snapshot_events:
        return CodeEvolutionResponse(data=[])

    # Extract snapshot_ids from payloads
    snapshot_ids = []
    for ev in snapshot_events:
        payload = ev.payload if isinstance(ev.payload, dict) else {}
        sid = payload.get("snapshot_id")
        if sid:
            try:
                snapshot_ids.append(uuid.UUID(str(sid)))
            except (ValueError, TypeError):
                pass

    if not snapshot_ids:
        return CodeEvolutionResponse(data=[])

    # Fetch actual code snapshots from operational schema
    snap_stmt = (
        select(CodeSnapshot)
        .where(CodeSnapshot.id.in_(snapshot_ids))
        .order_by(CodeSnapshot.snapshot_at)
    )
    snap_result = await db.execute(snap_stmt)
    snapshots = list(snap_result.scalars().all())

    entries = [
        CodeSnapshotEntry(
            snapshot_id=str(s.id),
            code=s.code,
            snapshot_at=s.snapshot_at,
        )
        for s in snapshots
    ]

    return CodeEvolutionResponse(data=entries)
