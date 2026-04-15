from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.shared.db.session import get_async_session
from app.shared.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)

_BLACKLIST_PREFIX = "auth:blacklist:"

# ---------------------------------------------------------------------------
# Redis dependency
# ---------------------------------------------------------------------------

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_pool


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    if credentials is None:
        raise AuthenticationError(message="Authentication required")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    jti = payload.get("jti")
    if jti:
        is_blacklisted = await redis.exists(f"{_BLACKLIST_PREFIX}{jti}") > 0
        if is_blacklisted:
            raise AuthenticationError(message="Token has been revoked")

    import uuid
    user_id = uuid.UUID(payload["sub"])

    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True)).limit(1)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(message="User not found or inactive")

    return user


def require_role(*roles: str) -> Callable:
    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role.value not in roles:
            raise AuthorizationError(
                message=f"Role '{current_user.role.value}' is not authorized for this resource"
            )
        return current_user

    return Depends(_check_role)


# Typed aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]
