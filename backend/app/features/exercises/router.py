from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser, require_role
from app.features.exercises.schemas import (
    ExerciseCreateRequest,
    ExerciseResponse,
    ExerciseSummaryResponse,
    ExerciseUpdateRequest,
)
from app.features.exercises.services import ExerciseService
from app.shared.db.session import get_async_session
from app.shared.models.exercise import ExerciseDifficulty
from app.shared.schemas.response import PaginatedResponse, PaginationMeta, StandardResponse

router = APIRouter(prefix="/api/v1", tags=["exercises"])


# ---------------------------------------------------------------------------
# Exercises within a course (docente creates, all list)
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/exercises")
async def list_course_exercises(
    course_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    difficulty: ExerciseDifficulty | None = None,
    topic: str | None = None,
) -> dict:
    service = ExerciseService(session)
    items, total = await service.list_by_course(
        course_id, page=page, per_page=per_page, difficulty=difficulty, topic=topic,
    )
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[ExerciseSummaryResponse.model_validate(e) for e in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    ).model_dump()


@router.post("/courses/{course_id}/exercises", status_code=status.HTTP_201_CREATED)
async def create_exercise(
    course_id: uuid.UUID,
    body: ExerciseCreateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ExerciseService(session)
    exercise = await service.create(course_id, body.model_dump())
    await session.commit()
    return StandardResponse(data=ExerciseResponse.model_validate(exercise)).model_dump()


# ---------------------------------------------------------------------------
# Individual exercise
# ---------------------------------------------------------------------------


@router.get("/exercises/{exercise_id}")
async def get_exercise(
    exercise_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ExerciseService(session)

    # Alumno: emit reads_problem event. Docente/admin: just fetch.
    if current_user.role.value == "alumno":
        exercise = await service.get_for_student(exercise_id, current_user.id)
        await session.commit()
    else:
        exercise = await service.get(exercise_id)

    return StandardResponse(data=ExerciseResponse.model_validate(exercise)).model_dump()


@router.put("/exercises/{exercise_id}")
async def update_exercise(
    exercise_id: uuid.UUID,
    body: ExerciseUpdateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ExerciseService(session)
    exercise = await service.update(exercise_id, body.model_dump(exclude_unset=True))
    await session.commit()
    return StandardResponse(data=ExerciseResponse.model_validate(exercise)).model_dump()


@router.delete("/exercises/{exercise_id}")
async def delete_exercise(
    exercise_id: uuid.UUID,
    _user=require_role("admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = ExerciseService(session)
    await service.delete(exercise_id)
    await session.commit()
    return {"status": "ok", "data": None}


# ---------------------------------------------------------------------------
# Student exercises (across enrolled courses)
# ---------------------------------------------------------------------------


@router.get("/student/exercises")
async def student_exercises(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    difficulty: ExerciseDifficulty | None = None,
    topic: str | None = None,
) -> dict:
    service = ExerciseService(session)
    items, total = await service.list_for_student(
        current_user.id, page=page, per_page=per_page, difficulty=difficulty, topic=topic,
    )
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[ExerciseSummaryResponse.model_validate(e) for e in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    ).model_dump()
