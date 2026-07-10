from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.activity import Activity


class ActivityRepository(Protocol):
    """Outbound port for Activity persistence."""

    def insert(self, activity: Activity) -> Activity:
        """Store a new activity row and return it."""
        ...

    def list_by_party(self, party_id: str) -> list[Activity]:
        """Return activities for a party ordered by occurred_at DESC (newest first)."""
        ...

    def get_by_id(self, activity_id: str) -> Optional[Activity]:
        """Return one activity by id, or None if it does not exist."""
        ...

    def find_open_draft(self, staff_user_id: str, party_id: str) -> Optional[Activity]:
        """Return the most recent status='draft' row for (staff, party), or None."""
        ...

    def update(self, activity: Activity) -> Activity:
        """Persist every mutable field of an existing activity row (full overwrite,
        keyed by activity_id). party_id/staff_user_id/created_at are immutable and
        not part of the UPDATE — activity_id is the only identity column."""
        ...
