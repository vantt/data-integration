from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.profile import Note, PartyTag, Tag


class TagRepository(Protocol):
    """Outbound port for crm_tag + crm_party_tag persistence."""

    def list_tags(self, category: Optional[str] = None) -> list[Tag]:
        """Return all tags, optionally filtered by category (None = all)."""
        ...

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Return a single tag by tag_id, or None if not found."""
        ...

    def create_tag(self, tag: Tag) -> None:
        """Insert a new tag; UNIQUE(category, name) enforced at DB level."""
        ...

    def update_tag(self, tag: Tag) -> None:
        """Update name, display_label, category, color of an existing tag."""
        ...

    def delete_tag(self, tag_id: str) -> None:
        """Delete a tag by tag_id."""
        ...

    def attach_tag(self, party_tag: PartyTag) -> None:
        """Create a crm_party_tag row (INSERT OR IGNORE — idempotent on duplicate)."""
        ...

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        """Remove a crm_party_tag row for the given party and tag."""
        ...

    def list_party_tags(self, party_id: str) -> list[Tag]:
        """Return all Tag objects currently attached to party_id."""
        ...

    def list_party_tags_with_meta(self, party_id: str) -> list[PartyTag]:
        """Return PartyTag objects (with tagged_by / tagged_at) for all tags on a party."""
        ...


class NoteRepository(Protocol):
    """Outbound port for crm_note persistence."""

    def add_note(self, note: Note) -> None:
        """Insert a new note for a party."""
        ...

    def list_notes(self, party_id: str, limit: int = 50) -> list[Note]:
        """Return notes for party_id ordered by pinned DESC, created_at DESC."""
        ...

    def update_note(
        self,
        note_id: str,
        body: str,
        note_type: str = "general",
        pinned: bool = False,
        visibility: str = "team",
    ) -> None:
        """Update mutable note fields (body, note_type, pinned, visibility)."""
        ...

    def soft_delete_note(self, note_id: str) -> None:
        """Set deleted_at to now — note remains in DB but is treated as deleted."""
        ...
