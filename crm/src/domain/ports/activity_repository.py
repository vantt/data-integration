from __future__ import annotations

from typing import Protocol

from domain.entities.activity import Activity


class ActivityRepository(Protocol):
    """Outbound port for Activity persistence."""

    def insert(self, activity: Activity) -> Activity:
        """Store a new activity row and return it."""
        ...

    def list_by_party(self, party_id: str) -> list[Activity]:
        """Return activities for a party ordered by occurred_at DESC (newest first)."""
        ...
