"""Unit tests for TutorRateLimiter — mocked Redis."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.tutor.rate_limiter import TutorRateLimiter


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock()
    redis.pipeline.return_value = pipe
    return redis, pipe


@pytest.fixture
def mock_settings():
    with patch("app.features.tutor.rate_limiter.get_settings") as mock:
        settings = MagicMock()
        settings.tutor_rate_limit_per_hour = 30
        mock.return_value = settings
        yield settings


async def test_allows_when_under_limit(mock_redis, mock_settings):
    redis, pipe = mock_redis
    pipe.execute.return_value = [None, 5, [b"12345", b"0"]]  # zremrangebyscore, zcard=5, TIME

    pipe2 = AsyncMock()
    pipe2.execute = AsyncMock()
    redis.pipeline.side_effect = [pipe, pipe2]

    limiter = TutorRateLimiter(redis)
    result = await limiter.check(uuid.uuid4(), uuid.uuid4())

    assert result.allowed is True
    assert result.remaining == 24  # 30 - 5 - 1


async def test_denies_when_at_limit(mock_redis, mock_settings):
    redis, pipe = mock_redis
    pipe.execute.return_value = [None, 30, [b"12345", b"0"]]

    limiter = TutorRateLimiter(redis)
    result = await limiter.check(uuid.uuid4(), uuid.uuid4())

    assert result.allowed is False
    assert result.remaining == 0
