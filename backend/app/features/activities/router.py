from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser, require_role
from app.features.activities.schemas import (
    ActivityResponse,
    ActivityUpdateRequest,
    GenerateActivityRequest,
    LLMConfigRequest,
    LLMConfigResponse,
)
from app.features.activities.services import ActivityService, LLMConfigService
from app.features.activities.generation import ActivityGenerationService
from app.features.exercises.schemas import ExerciseResponse
from app.shared.db.session import get_async_session
from app.shared.schemas.response import PaginatedResponse, PaginationMeta, StandardResponse

router = APIRouter(prefix="/api/v1", tags=["activities"])


# ---------------------------------------------------------------------------
# LLM Settings
# ---------------------------------------------------------------------------


@router.get("/settings/llm")
async def get_llm_config(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = LLMConfigService(session)
    config = await service.get(current_user.id)
    if config is None:
        return StandardResponse(data=None).model_dump()
    return StandardResponse(
        data=LLMConfigResponse(
            provider=config.provider,
            model_name=config.model_name,
        ),
    ).model_dump()


@router.put("/settings/llm")
async def save_llm_config(
    body: LLMConfigRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = LLMConfigService(session)
    config = await service.save(
        user_id=current_user.id,
        provider=body.provider,
        api_key=body.api_key,
        model_name=body.model_name,
    )
    await session.commit()
    return StandardResponse(
        data=LLMConfigResponse(provider=config.provider, model_name=config.model_name),
    ).model_dump()


@router.post("/settings/llm/test")
async def test_llm_config(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Test the saved LLM configuration by making a minimal API call."""
    from app.core.llm import get_adapter

    service = LLMConfigService(session)
    config = await service.get(current_user.id)
    if config is None:
        return StandardResponse(data={"status": "error", "message": "No hay API key configurada."}).model_dump()

    api_key = service.decrypt_key(config)
    adapter = get_adapter(config.provider.value, api_key, config.model_name)

    try:
        result = await adapter.generate(
            [{"role": "user", "content": "Responde solo con la palabra OK"}],
            max_tokens=10,
            temperature=0,
        )
        return StandardResponse(data={"status": "ok", "response": result.strip()}).model_dump()
    except Exception as exc:
        return StandardResponse(data={"status": "error", "message": str(exc)[:200]}).model_dump()


# ---------------------------------------------------------------------------
# Activity Generation
# ---------------------------------------------------------------------------


@router.post("/activities/generate", status_code=status.HTTP_201_CREATED)
async def generate_activity(
    body: GenerateActivityRequest,
    current_user: CurrentUser,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ActivityGenerationService(session)
    activity = await service.generate(
        user_id=current_user.id,
        course_id=body.course_id,
        prompt=body.prompt,
    )
    await session.commit()

    exercises = [ExerciseResponse.model_validate(e) for e in activity.exercises]
    data = ActivityResponse.model_validate(activity).model_dump()
    data["exercises"] = [e.model_dump() for e in exercises]
    return StandardResponse(data=data).model_dump()


# ---------------------------------------------------------------------------
# Activity CRUD
# ---------------------------------------------------------------------------


@router.get("/activities")
async def list_activities(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    service = ActivityService(session)
    items, total = await service.list_by_user(current_user.id, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[ActivityResponse.model_validate(a) for a in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    ).model_dump()


@router.get("/activities/{activity_id}")
async def get_activity(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ActivityService(session)
    activity = await service.get(activity_id)
    exercises = [ExerciseResponse.model_validate(e) for e in activity.exercises]
    data = ActivityResponse.model_validate(activity).model_dump()
    data["exercises"] = [e.model_dump() for e in exercises]
    return StandardResponse(data=data).model_dump()


@router.put("/activities/{activity_id}")
async def update_activity(
    activity_id: uuid.UUID,
    body: ActivityUpdateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ActivityService(session)
    await service.update(activity_id, body.model_dump(exclude_unset=True))
    await session.commit()
    activity = await service.get(activity_id)
    return StandardResponse(data=ActivityResponse.model_validate(activity)).model_dump()


@router.post("/activities/{activity_id}/publish")
async def publish_activity(
    activity_id: uuid.UUID,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ActivityService(session)
    await service.publish(activity_id)
    await session.commit()
    # Re-fetch after commit to avoid lazy-load issues
    activity = await service.get(activity_id)
    exercises = [ExerciseResponse.model_validate(e) for e in activity.exercises]
    data = ActivityResponse.model_validate(activity).model_dump()
    data["exercises"] = [e.model_dump() for e in exercises]
    return StandardResponse(data=data).model_dump()


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ActivityService(session)
    await service.delete(activity_id)
    await session.commit()
    return {"status": "ok", "data": None}


# ---------------------------------------------------------------------------
# Student view — published activities from enrolled courses
# ---------------------------------------------------------------------------


@router.get("/student/activities")
async def student_activities(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """List published activities from courses the student is enrolled in."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.shared.models.activity import Activity, ActivityStatus
    from app.shared.models.enrollment import Enrollment
    from app.shared.models.commission import Commission

    # Get course_ids for enrolled courses
    enrolled = await session.execute(
        select(Commission.course_id)
        .join(Enrollment, Enrollment.commission_id == Commission.id)
        .where(Enrollment.student_id == current_user.id, Enrollment.is_active.is_(True))
    )
    course_ids = [row[0] for row in enrolled.fetchall()]

    if not course_ids:
        return StandardResponse(data=[]).model_dump()

    result = await session.execute(
        select(Activity)
        .where(
            Activity.course_id.in_(course_ids),
            Activity.status == ActivityStatus.published,
            Activity.is_active.is_(True),
        )
        .options(selectinload(Activity.exercises))
        .order_by(Activity.created_at.desc())
    )
    activities = list(result.scalars().all())

    data = []
    for a in activities:
        act_data = ActivityResponse.model_validate(a).model_dump()
        act_data["exercise_count"] = len([e for e in a.exercises if e.is_active])
        data.append(act_data)

    return StandardResponse(data=data).model_dump()
