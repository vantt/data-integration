"""Application service — Worklist query assembly.

Thin facade over the two repositories that screen_worklist previously
received directly. Centralises the data-fetching boundary so business
rules (ownership filters, audit trails, etc.) can be added here without
touching the screen adapter layer.
"""
from __future__ import annotations

import threading
import time
from typing import Optional, Protocol

from domain.entities.cache_insight import ActionQueueItem
from domain.entities.last_contact import LastContact

# Action-queue TTL: data only changes when the reverse-ETL sync runs (hourly/daily).
# 60 s keeps HTMX polling fast while reflecting dismisses/snoozes within 1 minute.
_ACTION_QUEUE_TTL = 60.0


# ── Internal port protocols ────────────────────────────────────────────────────


class _ActionQueuePort(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...


class _LastContactPort(Protocol):
    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]: ...


# ── Service ────────────────────────────────────────────────────────────────────


class WorklistQueryService:
    """Aggregates action-queue and last-contact data for the worklist screen.

    Business rules that apply to the entire worklist (e.g. ownership filters,
    audit logging) should be added here, not in the screen adapter.
    """

    def __init__(
        self,
        action_queue: _ActionQueuePort,
        last_contact: Optional[_LastContactPort] = None,
    ) -> None:
        self._action_queue = action_queue
        self._last_contact = last_contact
        self._cache: list[ActionQueueItem] = []
        self._cache_ts: float = 0.0
        self._lock = threading.Lock()

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        """Return action queue items, serving from an in-process TTL cache.

        The underlying UNION ALL query joins 12 table references across two
        SQLite files; running it on every HTMX refresh is wasteful since the
        data only changes when the reverse-ETL sync runs (hourly/daily).
        Dismiss/snooze writes go to crm_action_state; they become visible on
        the next cache expiry (≤60 s).
        """
        now = time.monotonic()
        with self._lock:
            if self._cache and (now - self._cache_ts) < _ACTION_QUEUE_TTL:
                return self._cache
        result = self._action_queue.list_all_action_queue()
        with self._lock:
            self._cache = result
            self._cache_ts = time.monotonic()
        return result

    def invalidate_cache(self) -> None:
        """Force the next call to re-fetch from the database.

        Call after a dismiss/snooze so the UI reflects the change immediately
        rather than waiting for the TTL to expire.
        """
        with self._lock:
            self._cache_ts = 0.0

    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]:
        """Return last-contact data keyed by party_id.

        Returns an empty dict when last_contact is not configured.
        """
        if self._last_contact is None:
            return {}
        return self._last_contact.get_map_for_parties(party_ids)
