"""TagGovernanceService — business logic for the S13 Tag Governance Admin screen.

Phase 03 (260706-0833 crm-health-profile-tag-governance). Composes
SQLiteTagGovernanceRepository (raw admin queries/mutations) with the existing
TagService (attach_tag / create_tag / get_tag) so party-tag writes go through
the same code path used everywhere else (source tracking, commit semantics).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase
    from adapters.outbound.sqlite.tag_governance_repository import SQLiteTagGovernanceRepository

from application.tag_service import TagService
from domain.entities.profile import Tag


class TagGovernanceService:
    def __init__(
        self,
        repo: "SQLiteTagGovernanceRepository",
        tag_svc: TagService,
        db: Optional["CRMDatabase"] = None,
    ) -> None:
        self._repo = repo
        self._tags = tag_svc
        self._db = db

    # ── Taxonomy (Feature A) ──────────────────────────────────────────────────

    def list_categories(self) -> list[str]:
        return self._repo.list_categories()

    def list_tags_for_category(self, category: str) -> list[dict]:
        """Taxonomy tab rows — includes archived tags of this category so the
        admin can still find and [Bỏ lưu trữ] them (see repository docstring)."""
        rows = self._repo.list_tags_raw(category=category, is_provisional=0, include_archived=True)
        return self._enrich_rows(rows)

    def list_mergeable_tags(self, category: str) -> list[dict]:
        """Merge modal options for *category*: canonical tags (radio target
        candidates) plus L1 provisional tags (merge-away only)."""
        rows = self._repo.list_mergeable_tags_for_category(category)
        return [
            {
                "tag_id": r["tag_id"],
                "name": r["name"],
                "display_label": r["display_label"],
                "is_provisional": bool(r["is_provisional"]),
                "has_active_mapping": self._repo.has_active_mapping(r["tag_id"]),
            }
            for r in rows
        ]

    def pending_review_count(self) -> int:
        """L1 + L2 provisional tags + unreviewed chipify groups — badges the
        Settings "Tags" tab link so the queue doesn't silently pile up."""
        return self._repo.count_pending_review()

    def has_active_mapping(self, tag_id: str) -> bool:
        return self._repo.has_active_mapping(tag_id)

    def merge_tags(self, canonical_tag_id: str, merge_tag_ids: list[str]) -> None:
        ids = sorted({i for i in merge_tag_ids if i and i != canonical_tag_id})
        if not ids:
            raise ValueError("merge_tag_ids must contain at least one tag distinct from canonical_tag_id")
        self._repo.merge_tags(canonical_tag_id, ids)

    def archive_tag(self, tag_id: str) -> None:
        self._repo.archive_tag(tag_id)

    def unarchive_tag(self, tag_id: str) -> None:
        self._repo.unarchive_tag(tag_id)

    # ── Provisional queues (Features B/C) ─────────────────────────────────────

    def list_provisional_l1(self) -> list[dict]:
        rows = self._repo.list_tags_raw(is_provisional=1)
        return self._enrich_rows(rows)

    def list_provisional_l2(self) -> list[dict]:
        rows = self._repo.list_tags_raw(is_provisional=1, category_is_null=True)
        return self._enrich_rows(rows)

    def promote_l1(self, tag_id: str) -> None:
        self._repo.promote_l1(tag_id)

    def assign_category_and_promote_l2(self, tag_id: str, category: str) -> None:
        if not category.strip():
            raise ValueError("category is required to promote a Level 2 provisional tag")
        self._repo.assign_category_and_promote_l2(tag_id, category.strip())

    def rename_tag(self, tag_id: str, new_name: str) -> None:
        if not new_name.strip():
            raise ValueError("name is required")
        self._repo.rename_tag(tag_id, new_name.strip())

    def delete_provisional_tag(self, tag_id: str) -> None:
        self._repo.delete_provisional_tag(tag_id)

    def _enrich_rows(self, rows) -> list[dict]:
        out = []
        for r in rows:
            tag_id = r["tag_id"]
            out.append({
                "tag_id": tag_id,
                "name": r["name"],
                "display_label": r["display_label"],
                "category": r["category"],
                "color": r["color"],
                "is_archived": bool(r["is_archived"]),
                "usage_count": self._repo.usage_count(tag_id),
                "source_label": self._repo.source_label(tag_id),
                "has_active_mapping": self._repo.has_active_mapping(tag_id),
            })
        return out

    # ── Chipify (Feature D) ────────────────────────────────────────────────────

    def list_all_tags(self) -> list[Tag]:
        """All non-archived tags — backs the Chipify panel's "Map hiện có" dropdown."""
        return self._tags.list_tags("")

    def list_chipify_groups(self) -> list[dict]:
        return [{"raw_text": r["raw_text"], "n": r["n"]} for r in self._repo.list_chipify_groups()]

    def chipify_create_tag(
        self,
        raw_text: str,
        name: str,
        category: Optional[str],
        is_provisional: bool,
        color: str,
        display_label: str,
        actor_id: Optional[str],
    ) -> Tag:
        """Create a new tag from a chipify group, assign it to every party still
        carrying that raw text unreviewed, then mark the group reviewed."""
        tag = self._tags.create_tag(
            name=name, category=category or "", color=color, display_label=display_label,
            is_provisional=is_provisional,
        )
        self._assign_and_review(raw_text, tag.tag_id, actor_id)
        return tag

    def chipify_map_existing(self, raw_text: str, tag_id: str, actor_id: Optional[str]) -> None:
        tag = self._tags.get_tag(tag_id)
        if tag is None:
            raise ValueError(f"tag {tag_id!r} not found")
        self._assign_and_review(raw_text, tag_id, actor_id)

    def chipify_skip(self, raw_text: str) -> None:
        self._repo.mark_raw_text_reviewed(raw_text)

    def chipify_bulk_skip_all(self) -> None:
        self._repo.mark_all_unreviewed()

    def _assign_and_review(self, raw_text: str, tag_id: str, actor_id: Optional[str]) -> None:
        party_ids = self._repo.list_party_ids_for_raw_text(raw_text)
        for party_id in party_ids:
            self._tags.attach_tag(party_id, tag_id, actor_id, source="ops_normalized")
        self._repo.mark_raw_text_reviewed(raw_text)
