from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.auth.dependencies import require_role
from app.features.governance.schemas import (
    CreatePromptRequest,
    CreatePromptResponse,
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


@router.post(
    "/prompts",
    response_model=CreatePromptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new system prompt with semantic versioning",
)
async def create_prompt(
    body: CreatePromptRequest,
    session: AsyncSession = Depends(get_async_session),
    service: GovernanceService = Depends(get_governance_service),
    current_user: User = require_role("admin"),
) -> CreatePromptResponse:
    import hashlib
    from sqlalchemy import select
    from app.features.tutor.models import TutorSystemPrompt

    if body.change_type:
        active_stmt = (
            select(TutorSystemPrompt)
            .where(TutorSystemPrompt.is_active.is_(True))
            .order_by(TutorSystemPrompt.created_at.desc())
            .limit(1)
        )
        active_result = await session.execute(active_stmt)
        active_prompt = active_result.scalar_one_or_none()
        previous_version = active_prompt.version if active_prompt else None

        GovernanceService.validate_prompt_version(
            body.version, previous_version, body.change_type,
        )

    sha256_hash = hashlib.sha256(body.content.encode("utf-8")).hexdigest()

    prompt = TutorSystemPrompt(
        name=body.name,
        content=body.content,
        version=body.version,
        sha256_hash=sha256_hash,
        is_active=False,
        created_by=current_user.id,
        change_type=body.change_type,
        change_justification=body.change_justification,
    )
    session.add(prompt)
    await session.flush()

    await service.record_prompt_created(
        prompt_id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        sha256_hash=sha256_hash,
        created_by=current_user.id,
        change_type=body.change_type,
        change_justification=body.change_justification,
    )

    return CreatePromptResponse(
        data=PromptHistoryResponse.from_orm_uuid(prompt),
    )
