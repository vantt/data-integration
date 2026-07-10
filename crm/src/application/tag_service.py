"""TagService — business logic for party tags and tag definitions.

Depends only on domain entities and port protocols; no adapter imports.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from shared.timestamps import utc_now

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

from domain.entities.profile import PartyTag, Tag
from domain.ports.tag_repository import TagRepository


class TagService:
    """Manages tag lifecycle and party-tag associations."""

    def __init__(
        self,
        tag_repo: TagRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._tags = tag_repo
        self._db = db

    def attach_tag(
        self,
        party_id: str,
        tag_id: str,
        user_id: Optional[str] = None,
        source: str = "crm_user",
        source_activity_id: Optional[str] = None,
    ) -> None:
        """Attach a tag to a party.

        source_activity_id (migration 0044) links the attach back to the
        crm_activity_log row it was captured during (e.g. Log Activity /
        S14 call cockpit inline tagging) — optional and backward-compatible;
        omit or pass None when the tag is attached outside that flow (M03
        modal, sync, governance normalize).
        """
        tag = self._tags.get_tag(tag_id)
        if tag is None:
            raise ValueError(f"tag service: tag {tag_id!r} not found")
        pt = PartyTag(
            party_id=party_id,
            tag_id=tag_id,
            name=tag.name,
            tagged_at=utc_now(),
            category=tag.category,
            color=tag.color,
            tagged_by=user_id,
            source=source,
            source_activity_id=source_activity_id,
        )
        self._tags.attach_tag(pt)
        if self._db:
            self._db.commit()

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        self._tags.detach_tag(party_id, tag_id)
        if self._db:
            self._db.commit()

    def list_party_tags(self, party_id: str) -> list[PartyTag]:
        return self._tags.list_party_tags(party_id)

    def list_tags(self, category: str) -> list[Tag]:
        return self._tags.list_tags(category)

    def list_tags_by_category_ordered_by_usage(self, category: str) -> list[Tag]:
        return self._tags.list_tags_by_category_ordered_by_usage(category)

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self._tags.get_tag(tag_id)

    def create_tag(
        self,
        name: str,
        category: str,
        color: str,
        display_label: str = "",
        is_provisional: bool = False,
    ) -> Tag:
        """Create a tag definition.

        Phase 03 (260706-0833) — is_provisional=True allows category to stay
        NULL (Level 2 provisional: domain unknown, text-only). Canonical
        creation (is_provisional=False, the M14 modal default) keeps the
        pre-existing "general" fallback so untouched callers are unaffected.

        crm_tag's UNIQUE(category, name) does not block duplicates when
        category IS NULL — SQLite treats every NULL as distinct from every
        other NULL, so two L2 tags named the same thing insert cleanly at the
        DB level. Guard idempotently here instead: if an L2 tag with this name
        already exists, return it rather than creating a duplicate. Shared by
        both callers (TagGovernanceService.chipify_create_tag routes through
        this same method), so a single check covers both creation paths.
        """
        resolved_category = (category or None) if is_provisional else (category or "general")
        if resolved_category is None:
            existing = self._find_l2_tag_by_name(name)
            if existing is not None:
                return existing
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            display_label=display_label or None,
            category=resolved_category,
            color=color or "default",
            is_provisional=is_provisional,
        )
        self._tags.create_tag(tag)
        if self._db:
            self._db.commit()
        return tag

    def find_or_create_tag(
        self,
        name: str,
        category: Optional[str],
        is_provisional: bool = True,
        color: str = "default",
        display_label: str = "",
    ) -> Tag:
        """Idempotent lookup-or-create for rep-facing inline tag creation (S14/M03).

        Looks up an exact (category, name) match first — including archived
        tags, since crm_tag's UNIQUE(category, name) would otherwise raise on
        insert if the name collides with a previously archived tag, and two
        reps typing the same new concern should attach the same tag rather
        than spawn near-duplicate provisional rows for admin to clean up.
        L2 (category=None) dedup is handled inside create_tag itself.
        """
        if category:
            existing = self._tags.get_tag_by_name_category(name, category)
            if existing is not None:
                return existing
        return self.create_tag(
            name=name, category=category or "", color=color,
            display_label=display_label, is_provisional=is_provisional,
        )

    def _find_l2_tag_by_name(self, name: str) -> Optional[Tag]:
        """Case-sensitive match against existing L2 provisional tags (category
        IS NULL) — mirrors the column's current (non-collated) comparison
        behavior, so this check doesn't change matching semantics elsewhere."""
        for tag in self._tags.list_tags():
            if tag.category is None and tag.name == name:
                return tag
        return None

    def update_tag(self, tag_id: str, name: str, category: str, color: str, display_label: str = "") -> None:
        tag = Tag(
            tag_id=tag_id,
            name=name,
            display_label=display_label or None,
            category=category or "general",
            color=color or "default",
        )
        self._tags.update_tag(tag)
        if self._db:
            self._db.commit()

    def delete_tag(self, tag_id: str) -> None:
        self._tags.delete_tag(tag_id)
        if self._db:
            self._db.commit()
