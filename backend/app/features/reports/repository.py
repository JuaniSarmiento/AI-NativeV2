from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reports.models import CognitiveReport
from app.shared.repositories.base import BaseRepository


class CognitiveReportRepository(BaseRepository[CognitiveReport]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CognitiveReport)

    async def get_by_hash(
        self,
        student_id: uuid.UUID,
        activity_id: uuid.UUID,
        data_hash: str,
    ) -> CognitiveReport | None:
        stmt = select(CognitiveReport).where(
            CognitiveReport.student_id == student_id,
            CognitiveReport.activity_id == activity_id,
            CognitiveReport.data_hash == data_hash,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest(
        self,
        student_id: uuid.UUID,
        activity_id: uuid.UUID,
    ) -> CognitiveReport | None:
        stmt = (
            select(CognitiveReport)
            .where(
                CognitiveReport.student_id == student_id,
                CognitiveReport.activity_id == activity_id,
            )
            .order_by(desc(CognitiveReport.generated_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
