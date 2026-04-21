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
    TraceChatMessageResponse,
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
    activity_id: uuid.UUID | None = Query(None, description="Filter by activity (resolves its exercises)"),
    status: str | None = Query(None, description="open, closed, or invalidated"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: CognitiveService = Depends(get_cognitive_service),
    db: AsyncSession = Depends(get_async_session),
    _user: User = require_role("docente", "admin"),
) -> SessionListResponse:
    from sqlalchemy import select
    from app.shared.models.exercise import Exercise

    resolved_exercise_ids: list[uuid.UUID] | None = None
    if activity_id is not None:
        ex_result = await db.execute(
            select(Exercise.id).where(Exercise.activity_id == activity_id)
        )
        resolved_exercise_ids = [row[0] for row in ex_result.all()]

    items, total = await service._session_repo.get_sessions_by_commission(
        commission_id=commission_id,
        student_id=student_id,
        exercise_id=exercise_id,
        exercise_ids=resolved_exercise_ids,
        status=status,
        page=page,
        per_page=per_page,
    )

    exercise_ids = list({s.exercise_id for s in items})
    title_map: dict[uuid.UUID, str] = {}
    if exercise_ids:
        ex_result = await db.execute(
            select(Exercise.id, Exercise.title).where(Exercise.id.in_(exercise_ids))
        )
        for row in ex_result:
            title_map[row.id] = row.title

    total_pages = max(1, (total + per_page - 1) // per_page)
    return SessionListResponse(
        data=[
            SessionListItem.from_orm(s, exercise_title=title_map.get(s.exercise_id))
            for s in items
        ],
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
    db: AsyncSession = Depends(get_async_session),
    _user: User = require_role("docente", "admin"),
) -> TraceStandardResponse:
    from sqlalchemy import select
    from app.features.evaluation.schemas import CognitiveMetricsResponse
    from app.shared.models.exercise import Exercise

    trace = await service.get_trace(session_id)
    cog_session = trace["session"]

    user_row = (await db.execute(
        select(User).where(User.id == cog_session.student_id)
    )).scalar_one_or_none()

    exercise_row = (await db.execute(
        select(Exercise).where(Exercise.id == cog_session.exercise_id)
    )).scalar_one_or_none()

    session_resp = CognitiveSessionResponse.from_orm(cog_session)
    timeline = [TimelineEventResponse.from_orm(e) for e in trace["events"]]
    chat = [TraceChatMessageResponse.from_orm(m) for m in trace["chat"]]
    code_evo = [
        CodeSnapshotEntry(**entry) if isinstance(entry, dict) else entry
        for entry in trace["code_evolution"]
    ]
    metrics_dict = None
    anomalies = None
    if trace["metrics"] is not None:
        metrics_obj = trace["metrics"]
        metrics_dict = CognitiveMetricsResponse.from_orm(metrics_obj).model_dump()
        anomalies = getattr(metrics_obj, "coherence_anomalies", None)

    verify_result = None
    if trace["verification"] is not None:
        verify_result = VerifyResponse(**trace["verification"])

    return TraceStandardResponse(
        data=TraceResponse(
            session=session_resp,
            student_name=user_row.full_name if user_row else None,
            student_email=user_row.email if user_row else None,
            exercise_title=getattr(exercise_row, "title", None) if exercise_row else None,
            timeline=timeline,
            code_evolution=code_evo,
            chat=chat,
            metrics=metrics_dict,
            verification=verify_result,
            anomalies=anomalies,
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
