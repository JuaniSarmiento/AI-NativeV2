from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.exceptions import AuthenticationError
from app.core.security import decode_token
from app.features.auth.dependencies import CurrentUser, RedisClient, get_redis
from app.features.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.features.auth.service import AuthService
from app.shared.db.session import get_async_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=False)
_REFRESH_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth",
        max_age=_COOKIE_MAX_AGE,
        secure=False,  # Set True in production via config
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE,
        path="/api/v1/auth",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    service = AuthService(session, redis)
    user = await service.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    await session.commit()
    return {
        "status": "ok",
        "data": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    service = AuthService(session, redis)
    user = await service.authenticate(body.email, body.password)
    access_token, refresh_token, _, _ = service.create_token_pair(user)
    _set_refresh_cookie(response, refresh_token)

    return {
        "status": "ok",
        "data": TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        ).model_dump(),
    }


@router.post("/refresh")
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
    refresh_token: str | None = Cookie(None),
) -> dict:
    if not refresh_token:
        raise AuthenticationError(message="Refresh token not found")

    service = AuthService(session, redis)
    access_token, new_refresh, user = await service.refresh_tokens(refresh_token)
    _set_refresh_cookie(response, new_refresh)

    return {
        "status": "ok",
        "data": TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        ).model_dump(),
    }


@router.post("/logout")
async def logout(
    response: Response,
    current_user: CurrentUser,
    redis: RedisClient,
    session: AsyncSession = Depends(get_async_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    refresh_token: str | None = Cookie(None),
) -> dict:
    service = AuthService(session, redis)

    access_jti = None
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            access_jti = payload.get("jti")
        except Exception:
            pass

    await service.logout(
        access_jti=access_jti,
        refresh_token_str=refresh_token,
    )
    _clear_refresh_cookie(response)

    return {"status": "ok", "data": None}
