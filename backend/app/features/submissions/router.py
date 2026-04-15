from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser, require_role
from app.features.submissions.schemas import (
    ActivitySubmissionResponse,
    SnapshotRequest,
    SubmissionResponse,
    SubmitActivityRequest,
)
from app.features.submissions.services import SnapshotService, SubmissionService
from app.shared.db.session import get_async_session
from app.shared.schemas.response import StandardResponse

router = APIRouter(prefix="/api/v1", tags=["submissions"])


@router.post("/student/activities/{activity_id}/submit", status_code=status.HTTP_201_CREATED)
async def submit_activity(
    activity_id: uuid.UUID,
    body: SubmitActivityRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SubmissionService(session)
    activity_sub = await service.submit_activity(
        activity_id=activity_id,
        student_id=current_user.id,
        exercises_code=[{"exercise_id": ec.exercise_id, "code": ec.code} for ec in body.exercises],
    )
    await session.commit()

    # Re-fetch with relationships
    subs = await service.list_student_submissions(activity_id, current_user.id)
    latest = subs[0] if subs else activity_sub

    return StandardResponse(
        data=ActivitySubmissionResponse(
            id=latest.id,
            activity_id=latest.activity_id,
            student_id=latest.student_id,
            attempt_number=latest.attempt_number,
            status=latest.status.value,
            total_score=latest.total_score,
            submitted_at=latest.submitted_at,
            submissions=[SubmissionResponse.model_validate(s) for s in latest.submissions],
        ),
    ).model_dump()


@router.get("/student/activities/{activity_id}/submissions")
async def student_submissions(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SubmissionService(session)
    subs = await service.list_student_submissions(activity_id, current_user.id)
    data = [
        ActivitySubmissionResponse(
            id=s.id,
            activity_id=s.activity_id,
            student_id=s.student_id,
            attempt_number=s.attempt_number,
            status=s.status.value,
            total_score=s.total_score,
            submitted_at=s.submitted_at,
            submissions=[SubmissionResponse.model_validate(sub) for sub in s.submissions],
        )
        for s in subs
    ]
    return StandardResponse(data=data).model_dump()


@router.get("/activities/{activity_id}/submissions")
async def docente_submissions(
    activity_id: uuid.UUID,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SubmissionService(session)
    subs = await service.list_all_submissions(activity_id)
    data = [
        ActivitySubmissionResponse(
            id=s.id,
            activity_id=s.activity_id,
            student_id=s.student_id,
            attempt_number=s.attempt_number,
            status=s.status.value,
            total_score=s.total_score,
            submitted_at=s.submitted_at,
            submissions=[SubmissionResponse.model_validate(sub) for sub in s.submissions],
        )
        for s in subs
    ]
    return StandardResponse(data=data).model_dump()


@router.post("/student/exercises/{exercise_id}/snapshot", status_code=status.HTTP_201_CREATED)
async def save_snapshot(
    exercise_id: uuid.UUID,
    body: SnapshotRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SnapshotService(session)
    await service.save(current_user.id, exercise_id, body.code)
    await session.commit()
    return {"status": "ok", "data": None}
