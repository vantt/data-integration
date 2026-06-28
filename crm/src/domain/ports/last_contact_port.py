"""last_contact_port.py — domain port (Protocol) for last-contact persistence."""
from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.last_contact import LastContact


class LastContactPort(Protocol):
    """Outbound port for crm_last_contact read/write operations."""

    def upsert(
        self,
        party_id: str,
        activity_id: str,
        contacted_at: str,
        result: str,
        channel: Optional[str] = None,
    ) -> None:
        """Insert or update the last-contact snapshot for a party.

        Only advances the record when contacted_at is >= the stored value.
        """
        ...

    def get_by_party(self, party_id: str) -> Optional[LastContact]:
        """Return the LastContact snapshot for a single party, or None."""
        ...

    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]:
        """Return {party_id: LastContact} for all given party_ids in one query."""
        ...
