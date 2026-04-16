"""Repository for RiskAssessment persistence.

IMPORTANT: Repositories NEVER call session.commit(). The caller's
Unit of Work or transaction context owns commits.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.risk.models import RiskAssessment
from app.shared.repositories.base import BaseRepository


class RiskAssessmentRepository(BaseRepository[RiskAssessment]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RiskAssessment)

    async def get_by_commission(
        self,
        commission_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        risk_level: str | None = None,
    ) -> tuple[list[RiskAssessment], int]:
        base = select(RiskAssessment).where(
            RiskAssessment.commission_id == commission_id
        )
        if risk_level is not None:
            base = base.where(RiskAssessment.risk_level == risk_level)

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .order_by(RiskAssessment.assessed_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_student(
        self,
        student_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        commission_id: uuid.UUID | None = None,
    ) -> tuple[list[RiskAssessment], int]:
        base = select(RiskAssessment).where(
            RiskAssessment.student_id == student_id
        )
        if commission_id is not None:
            base = base.where(RiskAssessment.commission_id == commission_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .order_by(RiskAssessment.assessed_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_active_by_student_commission(
        self,
        student_id: uuid.UUID,
        commission_id: uuid.UUID,
    ) -> RiskAssessment | None:
        stmt = (
            select(RiskAssessment)
            .where(
                and_(
                    RiskAssessment.student_id == student_id,
                    RiskAssessment.commission_id == commission_id,
                    RiskAssessment.acknowledged_at.is_(None),
                )
            )
            .order_by(RiskAssessment.assessed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_daily(self, data: dict) -> RiskAssessment:
        """Insert or update a risk assessment for today.

        Application-level upsert: check if a row exists for the same
        student/commission/day, update it if so, create otherwise.
        The DB unique index prevents race-condition duplicates.
        """
        now = datetime.now(tz=timezone.utc)
        today = now.date()

        existing_stmt = (
            select(RiskAssessment)
            .where(
                and_(
                    RiskAssessment.student_id == data["student_id"],
                    RiskAssessment.commission_id == data["commission_id"],
                    cast(RiskAssessment.assessed_at, Date) == today,
                )
            )
            .limit(1)
        )
        result = await self._session.execute(existing_stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.risk_level = data["risk_level"]
            existing.risk_factors = data["risk_factors"]
            existing.recommendation = data.get("recommendation")
            existing.triggered_by = data["triggered_by"]
            existing.assessed_at = now
            await self._session.flush()
            return existing

        return await self.create({**data, "assessed_at": now})
