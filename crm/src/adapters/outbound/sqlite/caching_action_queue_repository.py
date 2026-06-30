"""Caching decorator for any ActionQueuePort.

Wraps a concrete action-queue repository with a TTL in-process cache so the
expensive UNION ALL query is not repeated on every HTMX refresh. The cache
is invalidated explicitly after dismiss/snooze writes.
"""
from __future__ import annotations

import threading
import time
from typing import Protocol

from domain.entities.cache_insight import ActionQueueItem

_TTL = 60.0


class _ActionQueuePort(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...


class CachingActionQueueRepository:
    """Transparent TTL cache decorator around any _ActionQueuePort."""

    def __init__(self, inner: _ActionQueuePort) -> None:
        self._inner = inner
        self._cache: list[ActionQueueItem] = []
        self._ts: float = 0.0
        self._lock = threading.Lock()

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        now = time.monotonic()
        with self._lock:
            if self._cache and (now - self._ts) < _TTL:
                return self._cache
        result = self._inner.list_all_action_queue()
        with self._lock:
            self._cache = result
            self._ts = time.monotonic()
        return result

    def invalidate_cache(self) -> None:
        with self._lock:
            self._ts = 0.0
