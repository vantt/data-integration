from __future__ import annotations

from typing import Protocol

from domain.entities.party import Party, PartyIdentity


class PartyRepository(Protocol):
    """Outbound port for persisting and querying Party golden records and their identities."""

    def find_by_identity(
        self, identity_type: str, identity_value: str
    ) -> Party | None:
        """Return the party that owns the given identity, or None if not found."""
        ...

    def create(self, party: Party) -> Party:
        """Insert a new party row and return it (with generated party_id)."""
        ...

    def get_by_id(self, party_id: str) -> Party | None:
        """Return a party by primary key, or None if not found."""
        ...

    def update(self, party: Party) -> None:
        """Persist changes to mutable party fields (display_name, primary_phone,
        primary_email, status, is_merged, merged_into)."""
        ...

    def list_by_phone(self, phone: str) -> list[Party]:
        """Return all non-merged parties with a matching normalised primary_phone."""
        ...

    def list_by_email(self, email: str) -> list[Party]:
        """Return all non-merged parties with a matching normalised primary_email."""
        ...

    def search_by_name(self, query: str) -> list[str]:
        """Run FTS MATCH on crm_party_fts and return matching party IDs."""
        ...

    def upsert_identity(self, identity: PartyIdentity) -> None:
        """Insert or ignore a party_identity row.
        UNIQUE(identity_type, identity_value) is the dedup guarantee.
        source_contact_quality is immutable — INSERT OR IGNORE semantics.
        contact_quality is mutable — UPDATE on conflict."""
        ...

    def list_identities(self, party_id: str) -> list[PartyIdentity]:
        """Return all identity rows for a given party."""
        ...

    def create_with_identities(
        self, party: Party, identities: list[PartyIdentity]
    ) -> Party:
        """Insert a party and all supplied identities in a single atomic transaction.
        Prevents an orphan party row when identity attachment fails mid-way."""
        ...

    def update_contact_quality(self, identity_id: str, contact_quality: str) -> None:
        """Update the mutable contact_quality field on an identity row.
        Valid values: masked | unverified | verified."""
        ...
