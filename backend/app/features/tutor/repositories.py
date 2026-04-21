from __future__ import annotations

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.features.tutor.models import TutorInteraction, TutorSystemPrompt
from app.shared.repositories.base import BaseRepository


class TutorInteractionRepository(BaseRepository[TutorInteraction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TutorInteraction)

    async def get_session_messages(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
        before: uuid.UUID | None = None,
    ) -> list[TutorInteraction]:
        stmt = (
            select(TutorInteraction)
            .where(TutorInteraction.session_id == session_id)
            .order_by(TutorInteraction.created_at.asc())
            .limit(limit)
        )
        if before is not None:
            subq = select(TutorInteraction.created_at).where(TutorInteraction.id == before).scalar_subquery()
            stmt = stmt.where(TutorInteraction.created_at < subq)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_session_messages(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[TutorInteraction]:
        """Get messages from the most recent session for this student+exercise."""
        latest_session = (
            select(TutorInteraction.session_id)
            .where(
                TutorInteraction.student_id == student_id,
                TutorInteraction.exercise_id == exercise_id,
            )
            .order_by(desc(TutorInteraction.created_at))
            .limit(1)
            .scalar_subquery()
        )

        stmt = (
            select(TutorInteraction)
            .where(
                TutorInteraction.student_id == student_id,
                TutorInteraction.exercise_id == exercise_id,
                TutorInteraction.session_id == latest_session,
            )
            .order_by(TutorInteraction.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_messages_for_cognitive_session(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
        started_at: "datetime",
        closed_at: "datetime | None" = None,
        *,
        limit: int = 200,
    ) -> list[TutorInteraction]:
        """Get tutor messages that fall within a cognitive session's time window."""
        stmt = (
            select(TutorInteraction)
            .where(
                TutorInteraction.student_id == student_id,
                TutorInteraction.exercise_id == exercise_id,
                TutorInteraction.created_at >= started_at,
            )
            .order_by(TutorInteraction.created_at.asc())
            .limit(limit)
        )
        if closed_at is not None:
            stmt = stmt.where(TutorInteraction.created_at <= closed_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_session_message_count(self, session_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(TutorInteraction)
            .where(TutorInteraction.session_id == session_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class TutorPromptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_prompt(self) -> TutorSystemPrompt:
        stmt = (
            select(TutorSystemPrompt)
            .where(TutorSystemPrompt.is_active.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError(resource="TutorSystemPrompt", message="No active system prompt found")
        return prompt
