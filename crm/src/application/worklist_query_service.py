"""Application service — Worklist query assembly.

Thin facade over the two repositories that screen_worklist previously
received directly. Centralises the data-fetching boundary so business
rules (ownership filters, audit trails, etc.) can be added here without
touching the screen adapter layer. TTL caching is handled by the outbound
adapter (CachingActionQueueRepository), not here.
"""
from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.cache_insight import ActionQueueItem
from domain.entities.last_contact import LastContact


# ── Internal port protocols ────────────────────────────────────────────────────


class _ActionQueuePort(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...
    def invalidate_cache(self) -> None: ...


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

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        return self._action_queue.list_all_action_queue()

    def invalidate_cache(self) -> None:
        self._action_queue.invalidate_cache()

    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]:
        """Return last-contact data keyed by party_id.

        Returns an empty dict when last_contact is not configured.
        """
        if self._last_contact is None:
            return {}
        return self._last_contact.get_map_for_parties(party_ids)
