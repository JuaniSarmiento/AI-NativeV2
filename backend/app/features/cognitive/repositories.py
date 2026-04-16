from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.cognitive.models import CognitiveEvent, CognitiveSession, SessionStatus
from app.shared.repositories.base import BaseRepository


class CognitiveSessionRepository(BaseRepository[CognitiveSession]):
    """Repository for :class:`CognitiveSession` persistence.

    Sessions are mutable (status, closed_at, session_hash can be updated)
    but events are immutable. Commits are NEVER called here — the caller's
    Unit of Work or session.begin() context owns the transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CognitiveSession)

    async def get_open_session(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
    ) -> CognitiveSession | None:
        """Return the open session for a student+exercise pair, or None.

        There should be at most one open session per (student, exercise) at
        any given time. If multiple open sessions exist (e.g. due to a crash),
        the most recently started one is returned.
        """
        stmt = (
            select(CognitiveSession)
            .where(
                CognitiveSession.student_id == student_id,
                CognitiveSession.exercise_id == exercise_id,
                CognitiveSession.status == "open",
            )
            .order_by(desc(CognitiveSession.started_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_with_events(
        self,
        session_id: uuid.UUID,
    ) -> CognitiveSession | None:
        """Return a session with its events eagerly loaded (selectinload).

        Events are ordered by sequence_number ASC via the relationship
        definition on the model.

        Returns None if the session does not exist.
        """
        stmt = (
            select(CognitiveSession)
            .where(CognitiveSession.id == session_id)
            .options(selectinload(CognitiveSession.events))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_stale_sessions(
        self,
        timeout_minutes: int = 30,
    ) -> list[CognitiveSession]:
        """Return open sessions with no new events for longer than timeout_minutes.

        A session is stale if:
          - status == open, AND
          - the most recent event was created more than timeout_minutes ago
            (or, if no events exist yet, started_at > timeout ago).

        Uses a correlated subquery to find the last event timestamp per session.
        """
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=timeout_minutes)

        # Subquery: latest created_at per session
        last_event_sq = (
            select(
                CognitiveEvent.session_id,
                CognitiveEvent.created_at.label("last_event_at"),
            )
            .order_by(
                CognitiveEvent.session_id,
                desc(CognitiveEvent.created_at),
            )
            .distinct(CognitiveEvent.session_id)
            .subquery("last_events")
        )

        # Sessions that are open AND whose last activity (event or start) predates cutoff
        stmt = (
            select(CognitiveSession)
            .outerjoin(
                last_event_sq,
                CognitiveSession.id == last_event_sq.c.session_id,
            )
            .where(
                CognitiveSession.status == "open",
                # Either there are no events and the session itself is old,
                # or the last event is older than the cutoff.
                (
                    (last_event_sq.c.last_event_at.is_(None) & (CognitiveSession.started_at < cutoff))
                    | (last_event_sq.c.last_event_at < cutoff)
                ),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


    async def get_sessions_by_commission(
        self,
        commission_id: uuid.UUID,
        student_id: uuid.UUID | None = None,
        exercise_id: uuid.UUID | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CognitiveSession], int]:
        """Return paginated sessions for a commission with optional filters."""
        from sqlalchemy import func as sa_func

        base = select(CognitiveSession).where(
            CognitiveSession.commission_id == commission_id
        )
        if student_id is not None:
            base = base.where(CognitiveSession.student_id == student_id)
        if exercise_id is not None:
            base = base.where(CognitiveSession.exercise_id == exercise_id)
        if status is not None:
            base = base.where(CognitiveSession.status == status)

        count_stmt = select(sa_func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .order_by(desc(CognitiveSession.started_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total


class CognitiveEventRepository(BaseRepository[CognitiveEvent]):
    """Repository for :class:`CognitiveEvent` persistence.

    Events are IMMUTABLE — this repository only provides read and create
    operations. There are no update or delete methods.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CognitiveEvent)

    async def get_last_event(
        self,
        session_id: uuid.UUID,
    ) -> CognitiveEvent | None:
        """Return the most recent event in the chain for the given session.

        Returns None if no events have been appended yet (fresh session).
        The previous_hash for the first event should then be genesis_hash.
        """
        stmt = (
            select(CognitiveEvent)
            .where(CognitiveEvent.session_id == session_id)
            .order_by(desc(CognitiveEvent.sequence_number))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_events_by_session(
        self,
        session_id: uuid.UUID,
    ) -> list[CognitiveEvent]:
        """Return all events for the session ordered by sequence_number ASC.

        Used by verify_chain to walk the chain from start to end.
        """
        stmt = (
            select(CognitiveEvent)
            .where(CognitiveEvent.session_id == session_id)
            .order_by(CognitiveEvent.sequence_number)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
