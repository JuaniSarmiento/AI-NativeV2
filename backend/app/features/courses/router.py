from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.dependencies import CurrentUser, require_role
from app.features.courses.schemas import (
    CommissionCreateRequest,
    CommissionResponse,
    CommissionUpdateRequest,
    CourseCreateRequest,
    CourseResponse,
    CourseUpdateRequest,
    EnrollmentResponse,
    StudentCourseResponse,
)
from app.features.courses.services import (
    CommissionService,
    CourseService,
    EnrollmentService,
)
from app.shared.db.session import get_async_session
from app.shared.schemas.response import PaginatedResponse, PaginationMeta, StandardResponse

router = APIRouter(prefix="/api/v1", tags=["courses"])


# ---------------------------------------------------------------------------
# Courses — CRUD (docente/admin)
# ---------------------------------------------------------------------------


@router.get("/courses")
async def list_courses(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    service = CourseService(session)
    # Docente sees only courses where they have commissions; admin sees all
    if current_user.role.value == "docente":
        items, total = await service.list_by_teacher(
            current_user.id, page=page, per_page=per_page
        )
    else:
        items, total = await service.list(page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[CourseResponse.model_validate(c) for c in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    ).model_dump()


@router.post("/courses", status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CourseService(session)
    course = await service.create(body.model_dump(exclude_unset=True))
    await session.commit()
    return StandardResponse(data=CourseResponse.model_validate(course)).model_dump()


@router.get("/courses/{course_id}")
async def get_course(
    course_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CourseService(session)
    course = await service.get(course_id)
    return StandardResponse(data=CourseResponse.model_validate(course)).model_dump()


@router.put("/courses/{course_id}")
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CourseService(session)
    course = await service.update(course_id, body.model_dump(exclude_unset=True))
    await session.commit()
    return StandardResponse(data=CourseResponse.model_validate(course)).model_dump()


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: uuid.UUID,
    _user=require_role("admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CourseService(session)
    await service.delete(course_id)
    await session.commit()
    return {"status": "ok", "data": None}


# ---------------------------------------------------------------------------
# Commissions — CRUD within a course (docente/admin)
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/commissions")
async def list_commissions(
    course_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    service = CommissionService(session)
    items, total = await service.list_by_course(course_id, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[CommissionResponse.model_validate(c) for c in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=total_pages),
    ).model_dump()


@router.post("/courses/{course_id}/commissions", status_code=status.HTTP_201_CREATED)
async def create_commission(
    course_id: uuid.UUID,
    body: CommissionCreateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CommissionService(session)
    commission = await service.create(course_id, body.model_dump())
    await session.commit()
    return StandardResponse(data=CommissionResponse.model_validate(commission)).model_dump()


@router.get("/commissions/{commission_id}")
async def get_commission(
    commission_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CommissionService(session)
    commission = await service.get(commission_id)
    return StandardResponse(data=CommissionResponse.model_validate(commission)).model_dump()


@router.put("/commissions/{commission_id}")
async def update_commission(
    commission_id: uuid.UUID,
    body: CommissionUpdateRequest,
    _user=require_role("docente", "admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CommissionService(session)
    commission = await service.update(commission_id, body.model_dump(exclude_unset=True))
    await session.commit()
    return StandardResponse(data=CommissionResponse.model_validate(commission)).model_dump()


@router.delete("/commissions/{commission_id}")
async def delete_commission(
    commission_id: uuid.UUID,
    _user=require_role("admin"),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = CommissionService(session)
    await service.delete(commission_id)
    await session.commit()
    return {"status": "ok", "data": None}


# ---------------------------------------------------------------------------
# Enrollment (alumno)
# ---------------------------------------------------------------------------


@router.post("/commissions/{commission_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll(
    commission_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = EnrollmentService(session)
    enrollment = await service.enroll(current_user.id, commission_id)
    await session.commit()
    return StandardResponse(data=EnrollmentResponse.model_validate(enrollment)).model_dump()


@router.get("/student/courses")
async def student_courses(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = EnrollmentService(session)
    enrollments = await service.list_student_courses(current_user.id)
    data = [
        StudentCourseResponse(
            course_id=str(e.commission.course.id),
            course_name=e.commission.course.name,
            commission_id=str(e.commission.id),
            commission_name=e.commission.name,
            teacher_name=e.commission.teacher.full_name,
            year=e.commission.year,
            semester=e.commission.semester,
            enrolled_at=e.enrolled_at,
        )
        for e in enrollments
    ]
    return StandardResponse(data=data).model_dump()
