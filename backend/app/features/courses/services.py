from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.features.courses.repositories import (
    CommissionRepository,
    CourseRepository,
    EnrollmentRepository,
)
from app.shared.models.commission import Commission
from app.shared.models.course import Course
from app.shared.models.enrollment import Enrollment
from app.shared.models.event_outbox import EventOutbox


class CourseService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CourseRepository(session)
        self._session = session

    async def create(self, data: dict[str, Any]) -> Course:
        existing = await self._repo.get_by_name(data["name"])
        if existing:
            raise ConflictError(message=f"A course named '{data['name']}' already exists.")
        return await self._repo.create(data)

    async def get(self, course_id: uuid.UUID) -> Course:
        return await self._repo.get_by_id(course_id)

    async def list(self, page: int = 1, per_page: int = 20) -> tuple[list[Course], int]:
        return await self._repo.list(page=page, per_page=per_page)

    async def list_by_teacher(
        self, teacher_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[Course], int]:
        return await self._repo.list_by_teacher(teacher_id, page=page, per_page=per_page)

    async def update(self, course_id: uuid.UUID, data: dict[str, Any]) -> Course:
        if "name" in data and data["name"]:
            existing = await self._repo.get_by_name(data["name"])
            if existing and existing.id != course_id:
                raise ConflictError(message=f"A course named '{data['name']}' already exists.")
        return await self._repo.update(course_id, data)

    async def delete(self, course_id: uuid.UUID) -> Course:
        return await self._repo.soft_delete(course_id)


class CommissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CommissionRepository(session)
        self._course_repo = CourseRepository(session)
        self._session = session

    async def create(self, course_id: uuid.UUID, data: dict[str, Any]) -> Commission:
        course = await self._course_repo.get_by_id(course_id)
        if not course.is_active:
            raise ValidationError(message="Cannot create commission for an inactive course.")
        data["course_id"] = course_id
        return await self._repo.create(data)

    async def get(self, commission_id: uuid.UUID) -> Commission:
        return await self._repo.get_by_id(commission_id)

    async def list_by_course(
        self, course_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[Commission], int]:
        return await self._repo.list_by_course(course_id, page=page, per_page=per_page)

    async def update(self, commission_id: uuid.UUID, data: dict[str, Any]) -> Commission:
        return await self._repo.update(commission_id, data)

    async def delete(self, commission_id: uuid.UUID) -> Commission:
        return await self._repo.soft_delete(commission_id)


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EnrollmentRepository(session)
        self._commission_repo = CommissionRepository(session)
        self._course_repo = CourseRepository(session)
        self._session = session

    async def enroll(self, student_id: uuid.UUID, commission_id: uuid.UUID) -> Enrollment:
        commission = await self._commission_repo.get_by_id(commission_id)
        if not commission.is_active:
            raise ValidationError(message="Cannot enroll in an inactive commission.")

        course = await self._course_repo.get_by_id(commission.course_id)
        if not course.is_active:
            raise ValidationError(message="Cannot enroll in a commission of an inactive course.")

        existing = await self._repo.find_by_student_and_commission(student_id, commission_id)
        if existing:
            raise ConflictError(message="You are already enrolled in this commission.")

        enrollment = await self._repo.create({
            "student_id": student_id,
            "commission_id": commission_id,
        })

        # Write outbox event for downstream consumers (Fase 3)
        outbox_event = EventOutbox(
            event_type="enrollment.created",
            payload={
                "enrollment_id": str(enrollment.id),
                "student_id": str(student_id),
                "commission_id": str(commission_id),
                "course_id": str(course.id),
            },
        )
        self._session.add(outbox_event)
        await self._session.flush()

        return enrollment

    async def list_student_courses(self, student_id: uuid.UUID) -> list[Enrollment]:
        return await self._repo.list_by_student(student_id)
