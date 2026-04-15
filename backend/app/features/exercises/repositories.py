from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.models.enrollment import Enrollment
from app.shared.models.exercise import Exercise, ExerciseDifficulty
from app.shared.repositories.base import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Exercise)

    async def list_by_course(
        self,
        course_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        difficulty: ExerciseDifficulty | None = None,
        topic: str | None = None,
    ) -> tuple[list[Exercise], int]:
        base = select(Exercise).where(
            Exercise.course_id == course_id,
            Exercise.is_active.is_(True),
        )

        if difficulty:
            base = base.where(Exercise.difficulty == difficulty)
        if topic:
            base = base.where(Exercise.topic_tags.any(topic))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .offset((page - 1) * per_page)
            .limit(per_page)
            .order_by(Exercise.order_index, Exercise.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_for_student(
        self,
        student_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
        difficulty: ExerciseDifficulty | None = None,
        topic: str | None = None,
    ) -> tuple[list[Exercise], int]:
        """Exercises from courses the student is enrolled in."""
        # Subquery: course_ids the student is enrolled in
        enrolled_courses = (
            select(Enrollment.commission_id)
            .where(Enrollment.student_id == student_id, Enrollment.is_active.is_(True))
        ).subquery()

        from app.shared.models.commission import Commission
        course_ids = (
            select(Commission.course_id)
            .where(Commission.id.in_(select(enrolled_courses.c.commission_id)))
        ).subquery()

        base = select(Exercise).where(
            Exercise.course_id.in_(select(course_ids.c.course_id)),
            Exercise.is_active.is_(True),
        )

        if difficulty:
            base = base.where(Exercise.difficulty == difficulty)
        if topic:
            base = base.where(Exercise.topic_tags.any(topic))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .offset((page - 1) * per_page)
            .limit(per_page)
            .order_by(Exercise.order_index, Exercise.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total
