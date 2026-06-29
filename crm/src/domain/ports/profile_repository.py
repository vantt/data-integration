from __future__ import annotations

from typing import Protocol

from domain.entities.customer360 import CustomerProfile, Party360


class ProfileRepository(Protocol):
    """Outbound port for crm_customer_profile persistence."""

    def get_profile(self, party_id: str) -> CustomerProfile | None:
        """Return the enrichment profile for party_id, or None if none exists yet."""
        ...

    def upsert_profile(self, profile: CustomerProfile) -> None:
        """Insert or replace the profile for a party (ON CONFLICT DO UPDATE)."""
        ...

    def update_custom_json(self, party_id: str, custom_json: str) -> None:
        """Replace the entire custom JSON column for a party profile.
        Caller must merge the existing JSON with new values before calling."""
        ...

    def get_party360(self, party_id: str) -> Party360 | None:
        """Query the crm_party_360 view for a single party.
        Returns None when the party does not exist or is merged."""
        ...


