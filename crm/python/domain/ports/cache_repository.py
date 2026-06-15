from __future__ import annotations

from typing import Protocol

from domain.entities.cache_insight import CacheInsight, ActionQueueItem
from domain.entities.party import PartySeed


class CacheRepository(Protocol):
    """Outbound port for reading from cache.db (ATTACHed read-only).

    All methods MUST gracefully handle the case where the wh_* tables do not yet
    exist (cache.db is empty before the first Python sync run) by returning
    None or an empty list with no error raised.
    """

    def get_customer_insight(self, customer_id: int) -> CacheInsight | None:
        """Return the cached insight, latest actions, and recent orders for the
        given Sapo customer_id.
        Returns None when no data exists or the cache tables are absent."""
        ...

    def list_party_seed(self) -> list[PartySeed]:
        """Return all rows from wh_party_seed that the seed consumer has not yet
        processed. Returns an empty list when the table is absent."""
        ...

    def list_all_action_queue(self) -> list[ActionQueueItem]:
        """Return all rows from wh_action_queue regardless of customer.
        Used by generate_tasks_from_action_queue to batch-convert actions to tasks.
        Returns an empty list (no error) when the table is absent."""
        ...
