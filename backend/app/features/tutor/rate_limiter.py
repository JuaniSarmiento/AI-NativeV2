from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "tutor:rate"
_WINDOW_SECONDS = 3600  # 1 hour


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: datetime


class TutorRateLimiter:
    """Sliding-window rate limiter using a Redis sorted set.

    Each message is an entry scored by its timestamp.  Before checking,
    entries older than the window are pruned.  Atomic via pipeline.
    """

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def check(
        self,
        student_id: uuid.UUID,
        exercise_id: uuid.UUID,
    ) -> RateLimitResult:
        settings = get_settings()
        limit = settings.tutor_rate_limit_per_hour

        key = f"{_KEY_PREFIX}:{student_id}:{exercise_id}"
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        pipe = self._redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.execute_command("TIME")
        results = await pipe.execute()

        current_count: int = results[1]

        if current_count >= limit:
            reset_at = datetime.fromtimestamp(now + _WINDOW_SECONDS, tz=timezone.utc)
            return RateLimitResult(allowed=False, remaining=0, reset_at=reset_at)

        # Add this request
        pipe2 = self._redis.pipeline(transaction=True)
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        pipe2.zadd(key, {member: now})
        pipe2.expire(key, _WINDOW_SECONDS + 60)
        await pipe2.execute()

        remaining = limit - current_count - 1
        reset_at = datetime.fromtimestamp(now + _WINDOW_SECONDS, tz=timezone.utc)

        return RateLimitResult(allowed=True, remaining=remaining, reset_at=reset_at)
