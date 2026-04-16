from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.models.commission import Commission
from app.shared.models.course import Course
from app.shared.models.enrollment import Enrollment
from app.shared.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Course)

    async def get_by_name(self, name: str) -> Course | None:
        stmt = (
            select(Course)
            .where(Course.name == name, Course.is_active.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_teacher(
        self,
        teacher_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Course], int]:
        """Return courses where the teacher owns a commission OR courses with no commissions yet."""
        from sqlalchemy import func, distinct, exists, or_

        has_own_commission = (
            exists()
            .where(
                Commission.course_id == Course.id,
                Commission.teacher_id == teacher_id,
                Commission.is_active.is_(True),
            )
        )
        has_no_commissions = (
            ~exists().where(
                Commission.course_id == Course.id,
                Commission.is_active.is_(True),
            )
        )

        base = (
            select(Course)
            .where(
                Course.is_active.is_(True),
                or_(has_own_commission, has_no_commissions),
            )
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .order_by(Course.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total


class CommissionRepository(BaseRepository[Commission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Commission)

    async def list_by_course(
        self,
        course_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Commission], int]:
        from sqlalchemy import func

        base = (
            select(Commission)
            .where(Commission.course_id == course_id, Commission.is_active.is_(True))
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .options(selectinload(Commission.teacher))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .order_by(Commission.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total


class EnrollmentRepository(BaseRepository[Enrollment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Enrollment)

    async def find_by_student_and_commission(
        self,
        student_id: uuid.UUID,
        commission_id: uuid.UUID,
    ) -> Enrollment | None:
        stmt = (
            select(Enrollment)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.commission_id == commission_id,
                Enrollment.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_student(
        self,
        student_id: uuid.UUID,
    ) -> list[Enrollment]:
        stmt = (
            select(Enrollment)
            .where(Enrollment.student_id == student_id, Enrollment.is_active.is_(True))
            .options(
                selectinload(Enrollment.commission).selectinload(Commission.course),
                selectinload(Enrollment.commission).selectinload(Commission.teacher),
            )
            .order_by(Enrollment.enrolled_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
