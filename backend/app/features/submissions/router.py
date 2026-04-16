from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser, require_role
from app.core.exceptions import AuthorizationError, NotFoundError
from app.features.submissions.schemas import (
    ActivityEvaluationResponse,
    ActivitySubmissionResponse,
    ConfirmActivityGradeRequest,
    CreateReflectionRequest,
    ReflectionResponse,
    SnapshotRequest,
    SubmissionResponse,
    SubmitActivityRequest,
)
from app.features.submissions.services import ReflectionService, SnapshotService, SubmissionService
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


@router.post(
    "/submissions/{activity_submission_id}/reflection",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse,
    tags=["reflections"],
)
async def create_reflection(
    activity_submission_id: uuid.UUID,
    body: CreateReflectionRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ReflectionService(session)
    reflection = await service.create_reflection(
        activity_submission_id=activity_submission_id,
        student_id=current_user.id,
        data=body.model_dump(),
    )
    await session.commit()
    return StandardResponse(data=ReflectionResponse.model_validate(reflection)).model_dump()


@router.get(
    "/submissions/{activity_submission_id}/reflection",
    response_model=StandardResponse,
    tags=["reflections"],
)
async def get_reflection(
    activity_submission_id: uuid.UUID,
    current_user: CurrentUser,
    _user=require_role("alumno", "docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ReflectionService(session)
    reflection = await service.get_reflection(activity_submission_id)
    if reflection is None:
        raise NotFoundError(resource="Reflection", identifier=str(activity_submission_id))

    # RBAC: alumnos can only access their own reflections
    if current_user.role == "alumno" and reflection.student_id != current_user.id:
        raise AuthorizationError(
            message="No tenés permiso para ver esta reflexión."
        )

    return StandardResponse(data=ReflectionResponse.model_validate(reflection)).model_dump()


# ---------------------------------------------------------------------------
# Grading — AI evaluation + docente confirmation
# ---------------------------------------------------------------------------


def _create_grading_service(session: AsyncSession):
    from app.features.submissions.grading import GradingService
    from app.features.tutor.llm_adapter import MistralAdapter
    from app.config import get_settings

    settings = get_settings()
    if settings.tutor_llm_provider == "anthropic":
        from app.features.tutor.llm_adapter import AnthropicAdapter
        llm = AnthropicAdapter()
    else:
        llm = MistralAdapter()
    return GradingService(session, llm)


def _build_activity_response(s) -> ActivitySubmissionResponse:
    student_name = ""
    try:
        if s.student is not None:
            student_name = getattr(s.student, "full_name", "") or ""
    except Exception:
        pass
    return ActivitySubmissionResponse(
        id=s.id,
        activity_id=s.activity_id,
        student_id=s.student_id,
        student_name=student_name,
        attempt_number=s.attempt_number,
        status=s.status.value,
        total_score=s.total_score,
        submitted_at=s.submitted_at,
        submissions=[SubmissionResponse.model_validate(sub) for sub in s.submissions],
    )


@router.post(
    "/teacher/activity-submissions/{activity_submission_id}/evaluate",
    tags=["grading"],
    summary="AI-evaluate all exercises in an activity submission",
)
async def evaluate_activity(
    activity_submission_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _user=require_role("docente", "admin"),
) -> dict:
    grading = _create_grading_service(session)
    result = await grading.evaluate_activity_submission(activity_submission_id)
    return StandardResponse(data=ActivityEvaluationResponse(**result)).model_dump()


@router.patch(
    "/teacher/activity-submissions/{activity_submission_id}/grade",
    tags=["grading"],
    summary="Docente confirms the AI grade for entire activity",
)
async def confirm_activity_grade(
    activity_submission_id: uuid.UUID,
    body: ConfirmActivityGradeRequest,
    session: AsyncSession = Depends(get_async_session),
    _user=require_role("docente", "admin"),
) -> dict:
    grading = _create_grading_service(session)
    activity_sub = await grading.confirm_activity_grade(
        activity_submission_id,
        body.general_score,
        body.general_feedback,
        [eg.model_dump() for eg in body.exercises],
    )
    await session.commit()
    return StandardResponse(data=_build_activity_response(activity_sub)).model_dump()


@router.get(
    "/teacher/activities/{activity_id}/pending",
    tags=["grading"],
    summary="List submissions for an activity (with student names)",
)
async def list_pending_submissions(
    activity_id: uuid.UUID,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SubmissionService(session)
    subs = await service.list_all_submissions(activity_id)
    data = [_build_activity_response(s) for s in subs]
    return StandardResponse(data=data).model_dump()


@router.get(
    "/student/activities/{activity_id}/grade",
    tags=["grading"],
    summary="Student views their grade and feedback",
)
async def student_grade(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = SubmissionService(session)
    subs = await service.list_student_submissions(activity_id, current_user.id)
    if not subs:
        return StandardResponse(data=None).model_dump()

    latest = subs[0]
    return StandardResponse(
        data=ActivitySubmissionResponse(
            id=latest.id,
            activity_id=latest.activity_id,
            student_id=latest.student_id,
            student_name=current_user.full_name or "",
            attempt_number=latest.attempt_number,
            status=latest.status.value,
            total_score=latest.total_score,
            submitted_at=latest.submitted_at,
            submissions=[SubmissionResponse.model_validate(sub) for sub in latest.submissions],
        ),
    ).model_dump()
