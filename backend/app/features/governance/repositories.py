from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.governance.models import GovernanceEvent
from app.shared.repositories.base import BaseRepository


class GovernanceEventRepository(BaseRepository[GovernanceEvent]):
    """Repository for :class:`GovernanceEvent` persistence.

    Governance events are append-only — there are no update or soft-delete
    operations. All queries are read-only besides ``create``.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GovernanceEvent)

    async def list_events(
        self,
        page: int = 1,
        per_page: int = 20,
        event_type: str | None = None,
    ) -> tuple[list[GovernanceEvent], int]:
        """Return a paginated list of governance events.

        Args:
            page: 1-based page number.
            per_page: Maximum items per page.
            event_type: Optional exact match filter on ``event_type``.

        Returns:
            A tuple of (items, total_count).
        """
        base = select(GovernanceEvent)

        if event_type is not None:
            base = base.where(GovernanceEvent.event_type == event_type)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Paginated query ordered by most recent first
        stmt = (
            base.order_by(GovernanceEvent.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total
