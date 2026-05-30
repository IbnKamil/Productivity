from __future__ import annotations

import json
import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class Cache:
    def __init__(self) -> None:
        settings = get_settings()
        self._memory: dict[str, tuple[float, str]] = {}
        self._client: Redis | None = None
        if settings.redis_url:
            try:
                self._client = Redis.from_url(settings.redis_url, decode_responses=True)
                self._client.ping()
            except RedisError:
                self._client = None

    def get_json(self, key: str) -> Any | None:
        if self._client:
            value = self._client.get(key)
            return json.loads(value) if value else None
        item = self._memory.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._memory.pop(key, None)
            return None
        return json.loads(value)

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, default=str)
        if self._client:
            self._client.setex(key, ttl_seconds, payload)
            return
        self._memory[key] = (time.time() + ttl_seconds, payload)

    def delete(self, key: str) -> None:
        if self._client:
            self._client.delete(key)
        self._memory.pop(key, None)


cache = Cache()
