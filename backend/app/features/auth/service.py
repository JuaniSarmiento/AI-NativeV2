from __future__ import annotations

import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.shared.models.user import User, UserRole

_BLACKLIST_PREFIX = "auth:blacklist:"


class AuthService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self._session = session
        self._redis = redis

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole,
    ) -> User:
        existing = await self._session.execute(
            select(User).where(User.email == email).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(message="A user with this email already exists.")

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        result = await self._session.execute(
            select(User).where(User.email == email, User.is_active.is_(True)).limit(1)
        )
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError(message="Invalid credentials")

        return user

    def create_token_pair(self, user: User) -> tuple[str, str, str, str]:
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())

        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            jti=access_jti,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            jti=refresh_jti,
        )

        return access_token, refresh_token, access_jti, refresh_jti

    async def refresh_tokens(self, refresh_token_str: str) -> tuple[str, str, User]:
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise AuthenticationError(message="Invalid token type")

        old_jti = payload["jti"]

        if await self.is_blacklisted(old_jti):
            raise AuthenticationError(message="Token has been revoked")

        user_id = uuid.UUID(payload["sub"])
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True)).limit(1)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationError(message="User not found or inactive")

        # Blacklist old refresh token
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        ttl = int((exp - datetime.now(tz=timezone.utc)).total_seconds())
        if ttl > 0:
            await self.blacklist_token(old_jti, ttl)

        access_token, new_refresh, _, _ = self.create_token_pair(user)
        return access_token, new_refresh, user

    async def logout(
        self,
        access_jti: str | None,
        refresh_token_str: str | None,
    ) -> None:
        settings = get_settings()

        if access_jti:
            ttl = settings.jwt_access_token_expire_minutes * 60
            await self.blacklist_token(access_jti, ttl)

        if refresh_token_str:
            try:
                payload = decode_token(refresh_token_str)
                refresh_jti = payload.get("jti")
                if refresh_jti:
                    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                    ttl = int((exp - datetime.now(tz=timezone.utc)).total_seconds())
                    if ttl > 0:
                        await self.blacklist_token(refresh_jti, ttl)
            except Exception:
                pass  # If refresh token is already invalid, nothing to blacklist

    async def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        key = f"{_BLACKLIST_PREFIX}{jti}"
        await self._redis.setex(key, ttl_seconds, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        key = f"{_BLACKLIST_PREFIX}{jti}"
        return await self._redis.exists(key) > 0
