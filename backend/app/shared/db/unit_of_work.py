from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.db.session import get_session_factory


class AsyncUnitOfWork:
    """Async Unit of Work — owns the transaction boundary.

    Repositories never call ``session.commit()`` directly.
    All writes are committed (or rolled back) exclusively here.

    Usage::

        async with AsyncUnitOfWork() as uow:
            repo = UserRepository(uow.session)
            user = await repo.create(data)
            await uow.commit()
            return user

    If ``commit()`` is never called, the context manager rolls back on exit.
    """

    def __init__(self) -> None:
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError(
                "UoW session is not initialized. "
                "Use `async with AsyncUnitOfWork() as uow:` before accessing session."
            )
        return self._session

    async def __aenter__(self) -> Self:
        factory = get_session_factory()
        self._session = factory()
        await self._session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

    async def commit(self) -> None:
        """Flush all pending changes and commit the transaction."""
        if self._session is None:
            raise RuntimeError("Cannot commit: session is not open.")
        await self._session.commit()

    async def rollback(self) -> None:
        """Discard all pending changes."""
        if self._session is None:
            return
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush pending changes without committing (useful for getting PKs)."""
        if self._session is None:
            raise RuntimeError("Cannot flush: session is not open.")
        await self._session.flush()
