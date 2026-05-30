from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import cache


LIMITS: dict[str, tuple[int, int]] = {
    "auth_login": (5, 600),
    "auth_register": (3, 3600),
    "reset_password": (3, 3600),
    "goals_create": (10, 60),
    "tasks_complete": (60, 60),
}

_windows: dict[str, deque[float]] = defaultdict(deque)


def _identity(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    forwarded_for = request.headers.get("x-forwarded-for")
    host = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    return f"ip:{host}"


def rate_limit(scope: str) -> Callable[[Request], None]:
    limit, window = LIMITS[scope]

    def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        key = f"rl:{scope}:{_identity(request)}"
        now = time.time()
        client = cache._client  # noqa: SLF001 - central cache owns Redis connection.
        if client:
            try:
                pipe = client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, window)
                _, _, count, _ = pipe.execute()
                if count > limit:
                    raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
                return
            except RedisError:
                pass

        timestamps = _windows[key]
        while timestamps and timestamps[0] <= now - window:
            timestamps.popleft()
        if len(timestamps) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
        timestamps.append(now)

    return dependency
