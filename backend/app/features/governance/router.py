from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.auth.dependencies import require_role
from app.features.governance.schemas import (
    GovernanceEventResponse,
    GovernanceEventsListResponse,
    GovernanceEventsMeta,
    PromptHistoryListResponse,
    PromptHistoryResponse,
)
from app.features.governance.service import GovernanceService
from app.shared.db.session import get_async_session
from app.shared.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


def get_governance_service(
    session: AsyncSession = Depends(get_async_session),
) -> GovernanceService:
    return GovernanceService(session)


@router.get(
    "/events",
    response_model=GovernanceEventsListResponse,
    summary="List governance events",
    description=(
        "Returns a paginated list of governance events. "
        "Supports optional filtering by event_type. Admin only."
    ),
)
async def list_governance_events(
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    per_page: Annotated[
        int, Query(ge=1, le=100, description="Items per page (max 100)")
    ] = 20,
    event_type: Annotated[
        str | None,
        Query(description="Filter by exact event_type (e.g. 'guardrail.triggered')"),
    ] = None,
    service: GovernanceService = Depends(get_governance_service),
    _user: User = require_role("admin"),
) -> GovernanceEventsListResponse:
    """List governance events — admin only.

    Returns events ordered by ``created_at`` descending (most recent first).
    """
    items, total = await service.list_events(
        page=page,
        per_page=per_page,
        event_type=event_type,
    )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    data = [GovernanceEventResponse.from_orm_uuid(item) for item in items]

    return GovernanceEventsListResponse(
        status="ok",
        data=data,
        meta=GovernanceEventsMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/prompts",
    response_model=PromptHistoryListResponse,
    summary="List system prompt history",
    description="Returns paginated list of tutor system prompts. Admin only.",
)
async def list_prompts(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_async_session),
    _user: User = require_role("admin"),
) -> PromptHistoryListResponse:
    from sqlalchemy import select, func as sa_func
    from app.features.tutor.models import TutorSystemPrompt

    base = select(TutorSystemPrompt)
    count_stmt = select(sa_func.count()).select_from(base.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    stmt = (
        base
        .order_by(TutorSystemPrompt.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())

    return PromptHistoryListResponse(
        status="ok",
        data=[PromptHistoryResponse.from_orm_uuid(p) for p in items],
        meta=GovernanceEventsMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages,
        ),
    )
