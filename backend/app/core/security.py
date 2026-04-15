from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    *,
    jti: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": jti or str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: uuid.UUID,
    *,
    jti: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": jti or str(uuid.uuid4()),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


_BLACKLIST_PREFIX = "auth:blacklist:"


async def validate_ws_token(token: str, redis: "Redis") -> dict:  # type: ignore[type-arg]
    """Validate a JWT from a WebSocket query param.

    Reusable outside of FastAPI's dependency system (no ``Depends``).
    Checks token validity, type, and blacklist in Redis.

    Returns the decoded payload dict on success.
    Raises ``AuthenticationError`` on any failure.
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(message="Invalid token type")

    jti = payload.get("jti")
    if jti:
        is_blacklisted = await redis.exists(f"{_BLACKLIST_PREFIX}{jti}") > 0
        if is_blacklisted:
            from app.core.exceptions import AuthenticationError
            raise AuthenticationError(message="Token has been revoked")

    return payload


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(message="Invalid or expired token") from exc
