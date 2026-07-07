"""SQLiteTagGovernanceRepository — raw SQL for the S13 Tag Governance Admin screen.

Phase 03 (260706-0833 crm-health-profile-tag-governance). Separate from
SQLiteTagRepository (which serves pickers/chips) because this screen needs
admin-only queries that intentionally break the "pickers only show canonical,
active tags" rule (e.g. archived rows must stay visible here for unarchive).

All multi-statement mutations (merge, archive) run inside CRMDatabase.transaction()
so a mid-way failure rolls back instead of leaving crm_tag / crm_party_tag /
crm_ext_tag_map partially updated.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from adapters.outbound.sqlite.connection import CRMDatabase


class SQLiteTagGovernanceRepository:
    """Implements the admin queries/mutations described in phase-03-tag-governance-admin.md."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── Taxonomy ──────────────────────────────────────────────────────────────

    def list_categories(self) -> list[str]:
        """Canonical categories — drives the dynamic tab list (Feature A)."""
        rows = self._db.conn.execute(
            "SELECT DISTINCT category FROM crm_tag "
            "WHERE is_provisional = 0 AND is_archived = 0 AND category IS NOT NULL "
            "ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]

    def list_tags_raw(
        self,
        *,
        category: Optional[str] = None,
        category_is_null: bool = False,
        is_provisional: int = 0,
        include_archived: bool = False,
    ) -> list[sqlite3.Row]:
        """Flexible tag listing. category_is_null=True → L2 queue (category IS NULL).

        include_archived=True is used by the taxonomy tab (so an archived tag
        stays reachable for [Bỏ lưu trữ]); provisional queues never include
        archived rows (an archived tag cannot also be pending review).
        """
        clauses = ["is_provisional = ?"]
        params: list = [is_provisional]
        if not include_archived:
            clauses.append("is_archived = 0")
        if category_is_null:
            clauses.append("category IS NULL")
        elif category is not None:
            clauses.append("category = ?")
            params.append(category)
        else:
            clauses.append("category IS NOT NULL")
        sql = (
            "SELECT tag_id, name, display_label, category, color, is_archived "
            f"FROM crm_tag WHERE {' AND '.join(clauses)} ORDER BY name"
        )
        return self._db.conn.execute(sql, params).fetchall()

    def get_tag_row(self, tag_id: str) -> Optional[sqlite3.Row]:
        return self._db.conn.execute(
            "SELECT tag_id, name, display_label, category, color, is_provisional, is_archived "
            "FROM crm_tag WHERE tag_id = ?",
            (tag_id,),
        ).fetchone()

    def count_pending_review(self) -> int:
        """L1 + L2 provisional tags + unreviewed chipify text groups.

        Lightweight badge count for the Settings "Tags" tab link — governance
        only helps against tag bloat if admins actually notice there's a queue
        to work through, so this backs a visible nudge rather than relying on
        someone remembering to open /settings/tags.
        """
        row = self._db.conn.execute(
            "SELECT "
            "  (SELECT COUNT(*) FROM crm_tag WHERE is_provisional = 1 AND is_archived = 0) AS provisional, "
            "  (SELECT COUNT(*) FROM (" + self._SQL_CHIPIFY_GROUPS + ")) AS chipify"
        ).fetchone()
        return int(row["provisional"]) + int(row["chipify"])

    def usage_count(self, tag_id: str) -> int:
        row = self._db.conn.execute(
            "SELECT COUNT(*) AS c FROM crm_party_tag WHERE tag_id = ?", (tag_id,)
        ).fetchone()
        return int(row["c"]) if row else 0

    def source_label(self, tag_id: str) -> str:
        """Best-effort 'Nguồn' column — crm_tag has no origin column of its own,
        so derive it from the most common crm_party_tag.source for this tag.
        A tag with zero assignments (e.g. freshly seeded) is labelled 'seeded'.
        """
        row = self._db.conn.execute(
            "SELECT source, COUNT(*) AS c FROM crm_party_tag WHERE tag_id = ? "
            "GROUP BY source ORDER BY c DESC LIMIT 1",
            (tag_id,),
        ).fetchone()
        return row["source"] if row else "seeded"

    def has_active_mapping(self, tag_id: str) -> bool:
        row = self._db.conn.execute(
            "SELECT 1 FROM crm_ext_tag_map WHERE crm_tag_id = ? AND is_active = 1 "
            "AND direction IN ('inbound', 'both') LIMIT 1",
            (tag_id,),
        ).fetchone()
        return row is not None

    def list_mergeable_tags_for_category(self, category: str) -> list[sqlite3.Row]:
        """Merge modal options: canonical tags (target-eligible) + L1 provisional
        tags (merge-away only) in the same category. Excludes archived rows."""
        return self._db.conn.execute(
            "SELECT tag_id, name, display_label, is_provisional FROM crm_tag "
            "WHERE category = ? AND is_archived = 0 ORDER BY is_provisional, name",
            (category,),
        ).fetchall()

    # ── Merge / archive (destructive — always transactional) ─────────────────

    def merge_tags(self, canonical_tag_id: str, merge_tag_ids: list[str]) -> None:
        """Reassign party_tag + repoint crm_ext_tag_map, then delete the merged tags.

        Exact 3-step order from phase-03-tag-governance-admin.md §A (FK-safe:
        ext_tag_map is repointed before crm_tag rows are deleted).
        """
        ids = [i for i in merge_tag_ids if i != canonical_tag_id]
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._db.transaction() as conn:
            # 1. Reassign party_tag. PK (party_id, tag_id): INSERT OR IGNORE the new
            #    pair then delete the old one — avoids a PK collision when a party
            #    already holds both the canonical tag and a tag being merged away.
            conn.execute(
                "INSERT OR IGNORE INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source, ext_ref) "
                f"SELECT party_id, ?, tagged_by, tagged_at, source, ext_ref FROM crm_party_tag "
                f"WHERE tag_id IN ({placeholders})",
                (canonical_tag_id, *ids),
            )
            conn.execute(
                f"DELETE FROM crm_party_tag WHERE tag_id IN ({placeholders})", ids
            )
            # 2. Repoint ACL mapping. UNIQUE(ext_tag_id, crm_tag_id) — dedupe (delete
            #    the merged-away mapping row) before repointing any survivor.
            conn.execute(
                f"DELETE FROM crm_ext_tag_map WHERE crm_tag_id IN ({placeholders}) "
                "AND EXISTS (SELECT 1 FROM crm_ext_tag_map m2 "
                "WHERE m2.ext_tag_id = crm_ext_tag_map.ext_tag_id AND m2.crm_tag_id = ?)",
                (*ids, canonical_tag_id),
            )
            conn.execute(
                f"UPDATE crm_ext_tag_map SET crm_tag_id = ? WHERE crm_tag_id IN ({placeholders})",
                (canonical_tag_id, *ids),
            )
            # 3. Delete the merged tags.
            conn.execute(f"DELETE FROM crm_tag WHERE tag_id IN ({placeholders})", ids)

    def archive_tag(self, tag_id: str) -> None:
        """Deactivate any active inbound/both mapping THEN archive the tag —
        prevents a zombie sync writing into a now-invisible tag."""
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE crm_ext_tag_map SET is_active = 0 "
                "WHERE crm_tag_id = ? AND is_active = 1 AND direction IN ('inbound', 'both')",
                (tag_id,),
            )
            conn.execute("UPDATE crm_tag SET is_archived = 1 WHERE tag_id = ?", (tag_id,))

    def unarchive_tag(self, tag_id: str) -> None:
        """Un-hide the tag. Deliberately does NOT reactivate crm_ext_tag_map —
        admin must re-enable sync mapping explicitly (intentional friction)."""
        self._db.conn.execute("UPDATE crm_tag SET is_archived = 0 WHERE tag_id = ?", (tag_id,))
        self._db.commit()

    # ── Provisional queue actions ─────────────────────────────────────────────

    def promote_l1(self, tag_id: str) -> None:
        self._db.conn.execute(
            "UPDATE crm_tag SET is_provisional = 0 WHERE tag_id = ? AND category IS NOT NULL",
            (tag_id,),
        )
        self._db.commit()

    def assign_category_and_promote_l2(self, tag_id: str, category: str) -> None:
        self._db.conn.execute(
            "UPDATE crm_tag SET category = ?, is_provisional = 0 WHERE tag_id = ?",
            (category, tag_id),
        )
        self._db.commit()

    def rename_tag(self, tag_id: str, new_name: str) -> None:
        self._db.conn.execute("UPDATE crm_tag SET name = ? WHERE tag_id = ?", (new_name, tag_id))
        self._db.commit()

    def delete_provisional_tag(self, tag_id: str) -> None:
        """Delete a provisional tag along with its party assignments.

        crm_ext_tag_map.crm_tag_id is a NOT NULL FK to crm_tag(tag_id) with no
        ON DELETE CASCADE (migration 0039) and foreign_keys=ON — deleting a tag
        that still has an ext mapping row pointing at it would otherwise raise
        an IntegrityError and abort the transaction. A provisional/L2 tag isn't
        expected to have one by design, but clean up defensively rather than
        let deletion crash (or silently leave an orphan) if it ever does.
        """
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM crm_ext_tag_map WHERE crm_tag_id = ?", (tag_id,))
            conn.execute("DELETE FROM crm_party_tag WHERE tag_id = ?", (tag_id,))
            conn.execute("DELETE FROM crm_tag WHERE tag_id = ?", (tag_id,))

    # ── Chipify (health_context_raw → structured tags) ───────────────────────

    _SQL_CHIPIFY_GROUPS = """
        SELECT
          json_extract(cp.custom, '$.health_context_raw') AS raw_text,
          COUNT(*) AS n
        FROM crm_customer_profile cp
        WHERE
          json_extract(cp.custom, '$.health_context_raw') IS NOT NULL
          AND (json_extract(cp.custom, '$.health_context_raw_reviewed') IS NULL
               OR json_extract(cp.custom, '$.health_context_raw_reviewed') = 'false')
        GROUP BY raw_text
        ORDER BY n DESC
    """

    def list_chipify_groups(self) -> list[sqlite3.Row]:
        return self._db.conn.execute(self._SQL_CHIPIFY_GROUPS).fetchall()

    def list_party_ids_for_raw_text(self, raw_text: str) -> list[str]:
        rows = self._db.conn.execute(
            "SELECT party_id FROM crm_customer_profile "
            "WHERE json_extract(custom, '$.health_context_raw') = ? "
            "AND (json_extract(custom, '$.health_context_raw_reviewed') IS NULL "
            "     OR json_extract(custom, '$.health_context_raw_reviewed') = 'false')",
            (raw_text,),
        ).fetchall()
        return [r["party_id"] for r in rows]

    def mark_raw_text_reviewed(self, raw_text: str) -> None:
        self._db.conn.execute(
            "UPDATE crm_customer_profile "
            "SET custom = json_set(custom, '$.health_context_raw_reviewed', 'true') "
            "WHERE json_extract(custom, '$.health_context_raw') = ? "
            "AND (json_extract(custom, '$.health_context_raw_reviewed') IS NULL "
            "     OR json_extract(custom, '$.health_context_raw_reviewed') = 'false')",
            (raw_text,),
        )
        self._db.commit()

    def mark_all_unreviewed(self) -> None:
        self._db.conn.execute(
            "UPDATE crm_customer_profile "
            "SET custom = json_set(custom, '$.health_context_raw_reviewed', 'true') "
            "WHERE json_extract(custom, '$.health_context_raw') IS NOT NULL "
            "AND (json_extract(custom, '$.health_context_raw_reviewed') IS NULL "
            "     OR json_extract(custom, '$.health_context_raw_reviewed') = 'false')"
        )
        self._db.commit()
