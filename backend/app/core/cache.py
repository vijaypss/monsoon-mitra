"""Tiny async-safe TTL cache. In-memory by default; swap for Redis via REDIS_URL.

Kept dependency-free so the prototype runs anywhere. The interface (get/set)
is intentionally Redis-compatible so a drop-in replacement is trivial.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 900, max_items: int = 1024) -> None:
        self._ttl = ttl_seconds
        self._max = max_items
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires, value = item
            if time.monotonic() > expires:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                # evict oldest-expiring entry
                oldest = min(self._store, key=lambda k: self._store[k][0])
                self._store.pop(oldest, None)
            self._store[key] = (time.monotonic() + (ttl or self._ttl), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
