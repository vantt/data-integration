from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.profile import Note, PartyTag, Tag


class TagRepository(Protocol):
    """Outbound port for crm_tag + crm_party_tag persistence."""

    def list_tags(self, category: Optional[str] = None) -> list[Tag]:
        """Return all tags, optionally filtered by category (None = all)."""
        ...

    def list_tags_by_category_ordered_by_usage(self, category: str) -> list[Tag]:
        """Return active (is_archived=0) tags in *category*, most-attached first.

        Used by S14 collect-row chip pickers (e.g. health_domain) so the most
        commonly assigned tags surface first.
        """
        ...

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Return a single tag by tag_id, or None if not found."""
        ...

    def get_tag_by_name_category(self, name: str, category: str) -> Optional[Tag]:
        """Return the tag matching (category, name) exactly, including archived ones.

        Used by TagService.find_or_create_tag to avoid a UNIQUE(category, name)
        IntegrityError when the requested name collides with a previously
        archived tag (list_tags/list_tags_by_category exclude archived rows,
        so that check alone would miss this case).
        """
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
        """Create a crm_party_tag row (INSERT OR IGNORE — idempotent on duplicate).

        Always writes party_tag.source explicitly (defaults to 'crm_user' on the
        dataclass) rather than relying on the column DEFAULT, so callers that
        need provenance (ops_normalized, sapo_v2_sync, merged) are unambiguous.
        """
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

    def list_party_tags_by_source(self, source: str) -> list[tuple[str, str]]:
        """Return (party_id, tag_id) pairs currently attached with the given source.

        Used by TagAclSyncService (source='sapo_v2_sync') to compute the current
        sync-owned set before diffing against the desired warehouse state.
        """
        ...

    def bulk_attach_synced(
        self, rows: list[tuple[str, str, Optional[str], str, Optional[str]]]
    ) -> None:
        """Batch-insert crm_party_tag rows with source='sapo_v2_sync'.

        rows: (party_id, tag_id, tagged_by, tagged_at, ext_ref). ON CONFLICT DO
        NOTHING — a pre-existing row on the same (party_id, tag_id) pair (e.g.
        'crm_user') survives untouched.
        """
        ...

    def bulk_detach_synced(self, pairs: list[tuple[str, str]], source: str) -> None:
        """Batch-delete crm_party_tag rows, filtering source=? in the SQL itself.

        Safety invariant: the DELETE can only ever remove rows matching *source*,
        regardless of what pairs are passed in — never touches a 'crm_user' row.
        """
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
