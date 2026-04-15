from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.shared.db.session import get_async_session


async def get_db_session(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[AsyncSession, None]:
    """Alias dependency — yields the per-request AsyncSession.

    Prefer importing this over ``get_async_session`` directly so that
    the abstraction layer is consistent across all routers.
    """
    yield session


# ---------------------------------------------------------------------------
# Typed aliases — use these in route signatures for cleaner annotations
# ---------------------------------------------------------------------------

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
