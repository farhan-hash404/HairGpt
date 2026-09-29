"""Redis-backed cache and counters, with an in-process fallback.

Redis is used where state must be shared across processes — the API workers
and the Celery workers: rate-limit counters and the evidence Q&A answer cache.
When REDIS_URL is unset or Redis is unreachable (e.g. a free single-container
demo host), everything falls back to per-process memory: slower to share, but
never an outage.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.core.config import settings

log = logging.getLogger("hairgpt.cache")

_client = None
_client_checked = False
_lock = threading.Lock()


def get_redis():
    """A connected Redis client, or None when unavailable."""
    global _client, _client_checked
    with _lock:
        if _client_checked:
            return _client
        _client_checked = True
        if not settings.redis_url:
            return None
        try:
            import redis

            client = redis.Redis.from_url(settings.redis_url, socket_timeout=1.0, socket_connect_timeout=1.0)
            client.ping()
            _client = client
            log.info("redis connected")
        except Exception as exc:
            log.warning("redis unavailable (%s); using in-process fallback", exc)
            _client = None
        return _client


def set_redis_client(client) -> None:
    """Inject a client (tests use fakeredis)."""
    global _client, _client_checked
    with _lock:
        _client, _client_checked = client, True


class _MemoryStore:
    def __init__(self):
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if expires and expires < time.time():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value, ttl: int) -> None:
        with self._lock:
            if len(self._data) > 5000:  # crude bound; this is only a fallback
                self._data.clear()
            self._data[key] = (time.time() + ttl if ttl else 0.0, value)

    def incr(self, key: str, ttl: int) -> int:
        with self._lock:
            expires, value = self._data.get(key, (time.time() + ttl, 0))
            if expires < time.time():
                expires, value = time.time() + ttl, 0
            value += 1
            self._data[key] = (expires, value)
            return value


_memory = _MemoryStore()


def reset_cache() -> None:
    """Forget the in-process store and re-detect Redis on next use (tests)."""
    global _client, _client_checked
    with _lock:
        _client, _client_checked = None, False
    _memory.__init__()


def cache_get(key: str) -> Any | None:
    client = get_redis()
    if client is not None:
        try:
            raw = client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            log.warning("redis get failed (%s)", exc)
    return _memory.get(key)


def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    client = get_redis()
    if client is not None:
        try:
            client.set(key, json.dumps(value), ex=ttl)
            return
        except Exception as exc:
            log.warning("redis set failed (%s)", exc)
    _memory.set(key, value, ttl)


def incr(key: str, ttl: int) -> int:
    """Atomic counter with expiry (INCR + EXPIRE on first increment)."""
    client = get_redis()
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl, nx=True)
            count, _ = pipe.execute()
            return int(count)
        except Exception as exc:
            log.warning("redis incr failed (%s)", exc)
    return _memory.incr(key, ttl)
