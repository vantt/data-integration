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
from domain.ports.profile_repository import TagRepository


class TagService:
    """Manages tag lifecycle and party-tag associations."""

    def __init__(
        self,
        tag_repo: TagRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._tags = tag_repo
        self._db = db

    def attach_tag(self, party_id: str, tag_id: str, user_id: Optional[str] = None) -> None:
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

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        return self._tags.get_tag(tag_id)

    def create_tag(self, name: str, category: str, color: str, display_label: str = "") -> Tag:
        tag = Tag(
            tag_id=str(uuid.uuid4()),
            name=name,
            display_label=display_label or None,
            category=category or "general",
            color=color or "default",
        )
        self._tags.create_tag(tag)
        if self._db:
            self._db.commit()
        return tag

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
