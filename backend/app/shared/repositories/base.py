from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.core.exceptions import NotFoundError
from app.shared.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository with CRUD operations.

    Repositories NEVER call ``session.commit()`` — that is the
    responsibility of the Unit of Work.
    """

    def __init__(self, session: AsyncSession, model_class: type[ModelType]) -> None:
        self._session = session
        self._model_class = model_class

    async def get_by_id(
        self,
        id: uuid.UUID,  # noqa: A002
        *,
        load_options: list[Any] | None = None,
        include_inactive: bool = False,
    ) -> ModelType:
        stmt = select(self._model_class).where(self._model_class.id == id)  # type: ignore[attr-defined]

        if load_options:
            for opt in load_options:
                stmt = stmt.options(opt)

        if not include_inactive and hasattr(self._model_class, "is_active"):
            stmt = stmt.where(self._model_class.is_active.is_(True))  # type: ignore[attr-defined]

        result = await self._session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance is None:
            raise NotFoundError(
                resource=self._model_class.__name__,
                identifier=str(id),
            )

        return instance

    async def list(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        load_options: list[Any] | None = None,
        include_inactive: bool = False,
        order_by: QueryableAttribute[Any] | None = None,
    ) -> tuple[list[ModelType], int]:
        base = select(self._model_class)

        if not include_inactive and hasattr(self._model_class, "is_active"):
            base = base.where(self._model_class.is_active.is_(True))  # type: ignore[attr-defined]

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Paginated query
        stmt = base.offset((page - 1) * per_page).limit(per_page)

        if load_options:
            for opt in load_options:
                stmt = stmt.options(opt)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self._model_class, "created_at"):
            stmt = stmt.order_by(self._model_class.created_at.desc())  # type: ignore[attr-defined]

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create(self, data: dict[str, Any]) -> ModelType:
        instance = self._model_class(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(
        self,
        id: uuid.UUID,  # noqa: A002
        data: dict[str, Any],
    ) -> ModelType:
        instance = await self.get_by_id(id)

        for key, value in data.items():
            setattr(instance, key, value)

        await self._session.flush()
        return instance

    async def soft_delete(self, id: uuid.UUID) -> ModelType:  # noqa: A002
        instance = await self.get_by_id(id)
        instance.is_active = False  # type: ignore[attr-defined]
        await self._session.flush()
        return instance
