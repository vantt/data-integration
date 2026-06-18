from __future__ import annotations

from typing import Protocol

from domain.entities.customer360 import CustomerProfile, CustomFieldDef, Party360
from domain.entities.tag import Tag, PartyTag
from domain.entities.note import Note


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


class CustomFieldRepository(Protocol):
    """Outbound port for crm_custom_field_def CRUD."""

    def list_active_defs(self, entity_type: str) -> list[CustomFieldDef]:
        """Return all active custom field definitions for entity_type
        (e.g. 'party'), ordered by sort_order."""
        ...

    def list_all_defs(self, entity_type: str) -> list[CustomFieldDef]:
        """Return all defs (active + inactive) for entity_type."""
        ...

    def get_def(self, field_id: str) -> CustomFieldDef | None:
        """Return a single definition by field_id, or None if not found."""
        ...

    def create_def(self, definition: CustomFieldDef) -> None:
        """Insert a new custom field definition."""
        ...

    def update_def(self, definition: CustomFieldDef) -> None:
        """Persist changes to label, options, is_required, is_active, sort_order."""
        ...


class TagRepository(Protocol):
    """Outbound port for crm_tag + crm_party_tag operations."""

    def list_tags(self, category: str) -> list[Tag]:
        """Return all tags, optionally filtered by category (empty = all)."""
        ...

    def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by tag_id, or None if not found."""
        ...

    def create_tag(self, tag: Tag) -> None:
        """Insert a new tag. UNIQUE(category, name) enforced at DB level."""
        ...

    def update_tag(self, tag: Tag) -> None:
        """Update name, category, color of an existing tag."""
        ...

    def delete_tag(self, tag_id: str) -> None:
        """Delete a tag by tag_id."""
        ...

    def attach_tag(self, party_tag: PartyTag) -> None:
        """Create a crm_party_tag row (INSERT OR IGNORE — idempotent on duplicate)."""
        ...

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        """Remove a crm_party_tag row."""
        ...

    def list_party_tags(self, party_id: str) -> list[Tag]:
        """Return all tags currently attached to party_id."""
        ...


class NoteRepository(Protocol):
    """Outbound port for crm_note persistence."""

    def add_note(self, note: Note) -> None:
        """Insert a new note for a party."""
        ...

    def list_notes(self, party_id: str) -> list[Note]:
        """Return notes for party_id ordered by created_at DESC."""
        ...
