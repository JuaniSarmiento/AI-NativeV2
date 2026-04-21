from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser
from app.shared.db.session import get_async_session
from app.shared.models.commission import Commission
from app.shared.models.enrollment import Enrollment
from app.shared.models.event_outbox import EventOutbox
from app.shared.models.exercise import Exercise
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/api/v1/student", tags=["cognitive-events"])

_ALLOWED_EVENT_TYPES = frozenset({
    "problem.reading_time",
    "problem.reread",
    "code.accepted_from_tutor",
})


class CognitiveEventRequest(BaseModel):
    event_type: str = Field(..., description="One of the allowed frontend event types")
    exercise_id: str = Field(..., description="Exercise UUID")
    payload: dict = Field(default_factory=dict)


@router.post(
    "/cognitive-events",
    response_model=StandardResponse,
    status_code=202,
    summary="Emit a cognitive event from the frontend",
)
async def emit_cognitive_event(
    body: CognitiveEventRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> StandardResponse:
    if body.event_type not in _ALLOWED_EVENT_TYPES:
        return StandardResponse(status="error", errors=[{"code": "INVALID_EVENT_TYPE", "message": f"Event type '{body.event_type}' is not allowed"}])

    try:
        exercise_id = uuid.UUID(body.exercise_id)
    except ValueError:
        return StandardResponse(status="error", errors=[{"code": "INVALID_UUID", "message": "Invalid exercise_id"}])

    # Resolve commission_id
    exercise_result = await session.execute(
        select(Exercise).where(Exercise.id == exercise_id)
    )
    exercise = exercise_result.scalar_one_or_none()
    if exercise is None:
        return StandardResponse(status="error", errors=[{"code": "NOT_FOUND", "message": "Exercise not found"}])

    commission_id = "00000000-0000-0000-0000-000000000000"
    enr_result = await session.execute(
        select(Enrollment).where(
            Enrollment.student_id == current_user.id,
            Enrollment.is_active.is_(True),
        )
    )
    for enr in enr_result.scalars().all():
        comm_result = await session.execute(
            select(Commission).where(
                Commission.id == enr.commission_id,
                Commission.course_id == exercise.course_id,
            )
        )
        if comm_result.scalar_one_or_none():
            commission_id = str(enr.commission_id)
            break

    session.add(EventOutbox(
        event_type=body.event_type,
        payload={
            "student_id": str(current_user.id),
            "exercise_id": str(exercise_id),
            "commission_id": commission_id,
            **body.payload,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
    ))
    await session.commit()

    return StandardResponse(status="ok", data={"accepted": True})
