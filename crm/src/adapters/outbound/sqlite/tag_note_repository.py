"""SQLite adapters for Tag, PartyTag, and Note entities.

Implements ports.TagRepository and ports.NoteRepository using raw sqlite3
queries ported from tag_queries.sql and note_queries.sql (Go sqlc source).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from adapters.outbound.sqlite.connection import CRMDatabase
from domain.entities.profile import Note, PartyTag, Tag


# ---------------------------------------------------------------------------
# SQLiteTagRepository
# ---------------------------------------------------------------------------

class SQLiteTagRepository:
    """Implements TagRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── SQL (ported from tag_queries.sql) ─────────────────────────────────────

    # Phase 03 (260706-0833): archived tags are retired from pickers (M03/M14)
    # while keeping crm_party_tag history intact — see tag_governance_repository
    # for the admin-side listing that DOES surface archived rows for unarchive.
    _SQL_LIST_ALL = """
        SELECT tag_id, name, display_label, category, color
        FROM crm_tag
        WHERE is_archived = 0
        ORDER BY category, name
    """

    _SQL_LIST_BY_CATEGORY = """
        SELECT tag_id, name, display_label, category, color
        FROM crm_tag
        WHERE category = ? AND is_archived = 0
        ORDER BY name
    """

    # Phase 02 (260706-0833): chip pickers (e.g. S14 health_domain) rank by
    # attach-count so commonly-used tags surface first. is_archived rows are
    # retired from pickers but keep their crm_party_tag history.
    _SQL_LIST_BY_CATEGORY_ORDERED_BY_USAGE = """
        SELECT t.tag_id, t.name, t.display_label, t.category, t.color
        FROM crm_tag t
        LEFT JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
        WHERE t.category = ? AND t.is_archived = 0
        GROUP BY t.tag_id
        ORDER BY COUNT(pt.party_id) DESC, t.name ASC
    """

    _SQL_GET = """
        SELECT tag_id, name, display_label, category, color
        FROM crm_tag
        WHERE tag_id = ?
        LIMIT 1
    """

    # Includes archived rows deliberately — see get_tag_by_name_category docstring.
    _SQL_GET_BY_NAME_CATEGORY = """
        SELECT tag_id, name, display_label, category, color
        FROM crm_tag
        WHERE category = ? AND name = ?
        LIMIT 1
    """

    _SQL_CREATE = """
        INSERT INTO crm_tag (tag_id, name, display_label, category, color, is_provisional)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    _SQL_UPDATE = """
        UPDATE crm_tag SET name = ?, display_label = ?, category = ?, color = ?
        WHERE tag_id = ?
    """

    _SQL_DELETE = """
        DELETE FROM crm_tag WHERE tag_id = ?
    """

    # Upsert (not INSERT OR IGNORE): attach_tag always represents a CRM-user action.
    # A pre-existing row on the same (party_id, tag_id) pair — e.g. one mirrored in
    # by TagAclSyncService with source='sapo_v2_sync' — is upgraded to 'crm_user' so
    # the next reconcile pass (which only ever touches source='sapo_v2_sync' rows)
    # leaves it alone from then on. See plan 260619-0830-crm-tag-acl-sync phase-03.
    _SQL_ATTACH = """
        INSERT INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(party_id, tag_id)
        DO UPDATE SET source = 'crm_user', tagged_by = excluded.tagged_by
    """

    _SQL_DETACH = """
        DELETE FROM crm_party_tag
        WHERE party_id = ? AND tag_id = ?
    """

    _SQL_LIST_BY_SOURCE = """
        SELECT party_id, tag_id FROM crm_party_tag WHERE source = ?
    """

    _SQL_BULK_ATTACH_SYNCED = """
        INSERT INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source, ext_ref)
        VALUES (?, ?, ?, ?, 'sapo_v2_sync', ?)
        ON CONFLICT(party_id, tag_id) DO NOTHING
    """

    _SQL_BULK_DETACH_SYNCED = """
        DELETE FROM crm_party_tag
        WHERE source = ? AND party_id = ? AND tag_id = ?
    """

    # Phase 03 (260706-0833): archived tags are retired from the party-facing
    # views (S14 cockpit, M03 modal) even if a prior crm_party_tag row exists —
    # otherwise an admin-archived tag becomes a "zombie" that keeps showing up
    # on any party it was tagged on before archival. crm_party_tag history is
    # untouched; only the surfaced tag list is filtered.
    _SQL_LIST_PARTY_TAGS = """
        SELECT t.tag_id, t.name, t.display_label, t.category, t.color
        FROM crm_tag t
        JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
        WHERE pt.party_id = ? AND t.is_archived = 0
        ORDER BY t.category, t.name
    """

    _SQL_LIST_PARTY_TAGS_WITH_META = """
        SELECT t.tag_id, t.name, t.display_label, t.category, t.color,
               pt.tagged_by, pt.tagged_at
        FROM crm_tag t
        JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
        WHERE pt.party_id = ? AND t.is_archived = 0
        ORDER BY t.category, t.name
    """

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_tag(row: sqlite3.Row) -> Tag:
        return Tag(
            tag_id=row["tag_id"],
            name=row["name"],
            display_label=row["display_label"],
            category=row["category"],
            color=row["color"],
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def list_tags(self, category: Optional[str] = None) -> list[Tag]:
        if category:
            rows = self._db.conn.execute(self._SQL_LIST_BY_CATEGORY, (category,)).fetchall()
        else:
            rows = self._db.conn.execute(self._SQL_LIST_ALL).fetchall()
        return [self._row_to_tag(r) for r in rows]

    def list_tags_by_category_ordered_by_usage(self, category: str) -> list[Tag]:
        rows = self._db.conn.execute(
            self._SQL_LIST_BY_CATEGORY_ORDERED_BY_USAGE, (category,)
        ).fetchall()
        return [self._row_to_tag(r) for r in rows]

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        row = self._db.conn.execute(self._SQL_GET, (tag_id,)).fetchone()
        return self._row_to_tag(row) if row else None

    def get_tag_by_name_category(self, name: str, category: str) -> Optional[Tag]:
        row = self._db.conn.execute(self._SQL_GET_BY_NAME_CATEGORY, (category, name)).fetchone()
        return self._row_to_tag(row) if row else None

    def create_tag(self, tag: Tag) -> None:
        self._db.conn.execute(
            self._SQL_CREATE,
            (tag.tag_id, tag.name, tag.display_label, tag.category, tag.color, 1 if tag.is_provisional else 0),
        )

    def update_tag(self, tag: Tag) -> None:
        self._db.conn.execute(self._SQL_UPDATE, (tag.name, tag.display_label, tag.category, tag.color, tag.tag_id))

    def delete_tag(self, tag_id: str) -> None:
        self._db.conn.execute(self._SQL_DELETE, (tag_id,))

    def attach_tag(self, party_tag: PartyTag) -> None:
        """Upsert — idempotent on duplicate (party_id, tag_id).

        Writes source explicitly (defaults to 'crm_user') rather than relying
        on the crm_party_tag.source column DEFAULT. On conflict (row already
        exists, e.g. sync-owned), the source is upgraded to 'crm_user' — a CRM
        user assigning a tag always wins over a prior sync mirror.
        """
        self._db.conn.execute(
            self._SQL_ATTACH,
            (party_tag.party_id, party_tag.tag_id, party_tag.tagged_by, party_tag.tagged_at,
             party_tag.source or "crm_user"),
        )

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        self._db.conn.execute(self._SQL_DETACH, (party_id, tag_id))

    def list_party_tags(self, party_id: str) -> list[Tag]:
        """Return Tag objects for all tags attached to party_id."""
        rows = self._db.conn.execute(self._SQL_LIST_PARTY_TAGS, (party_id,)).fetchall()
        return [self._row_to_tag(r) for r in rows]

    def list_party_tags_with_meta(self, party_id: str) -> list[PartyTag]:
        """Return PartyTag (with tagged_by / tagged_at) for all tags on a party."""
        rows = self._db.conn.execute(self._SQL_LIST_PARTY_TAGS_WITH_META, (party_id,)).fetchall()
        return [
            PartyTag(
                party_id=party_id,
                tag_id=r["tag_id"],
                name=r["name"],
                display_label=r["display_label"],
                category=r["category"],
                color=r["color"],
                tagged_by=r["tagged_by"],
                tagged_at=r["tagged_at"],
            )
            for r in rows
        ]

    def list_party_tags_by_source(self, source: str) -> list[tuple[str, str]]:
        """Return (party_id, tag_id) pairs currently attached with *source*.

        Used by TagAclSyncService to compute the current sync-owned set
        (source='sapo_v2_sync') before diffing against the desired warehouse state.
        """
        rows = self._db.conn.execute(self._SQL_LIST_BY_SOURCE, (source,)).fetchall()
        return [(row["party_id"], row["tag_id"]) for row in rows]

    def bulk_attach_synced(
        self, rows: list[tuple[str, str, Optional[str], str, Optional[str]]]
    ) -> None:
        """Batch-insert crm_party_tag rows with source='sapo_v2_sync'.

        rows: (party_id, tag_id, tagged_by, tagged_at, ext_ref). ON CONFLICT DO
        NOTHING — a pre-existing row on the same (party_id, tag_id) pair (e.g. a
        'crm_user' row) survives untouched; CRM user tags always win over sync.
        """
        if rows:
            self._db.conn.executemany(self._SQL_BULK_ATTACH_SYNCED, rows)

    def bulk_detach_synced(self, pairs: list[tuple[str, str]], source: str) -> None:
        """Batch-delete crm_party_tag rows, filtering source=? in the SQL itself.

        Safety invariant: the DELETE can only ever remove rows matching *source*
        (never a 'crm_user' row), even if the caller passes a stale pair list.
        """
        if pairs:
            self._db.conn.executemany(
                self._SQL_BULK_DETACH_SYNCED,
                [(source, party_id, tag_id) for (party_id, tag_id) in pairs],
            )


# ---------------------------------------------------------------------------
# SQLiteNoteRepository
# ---------------------------------------------------------------------------

class SQLiteNoteRepository:
    """Implements NoteRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── SQL (ported from note_queries.sql) ────────────────────────────────────

    _SQL_INSERT = """
        INSERT INTO crm_note (note_id, party_id, body, author_user_id, note_type, pinned, visibility, created_at, source_activity_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    _SQL_LIST = """
        SELECT note_id, party_id, body, author_user_id, created_at,
               note_type, pinned, visibility, task_id, source_activity_id, deleted_at
        FROM crm_note
        WHERE party_id = ?
        ORDER BY pinned DESC, created_at DESC
    """

    _SQL_UPDATE = """
        UPDATE crm_note
        SET body = ?, note_type = ?, pinned = ?, visibility = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE note_id = ?
    """

    _SQL_SOFT_DELETE = """
        UPDATE crm_note SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE note_id = ?
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def add_note(self, note: Note) -> None:
        self._db.conn.execute(self._SQL_INSERT, (
            note.note_id,
            note.party_id,
            note.body,
            note.author_user_id,
            note.note_type,
            1 if note.pinned else 0,
            note.visibility,
            note.created_at,
            note.source_activity_id,
        ))

    def list_notes(self, party_id: str, limit: int = 50) -> list[Note]:
        rows = self._db.conn.execute(self._SQL_LIST, (party_id,)).fetchmany(limit)
        return [
            Note(
                note_id=r["note_id"],
                party_id=r["party_id"],
                body=r["body"],
                author_user_id=r["author_user_id"],
                created_at=r["created_at"],
                note_type=r["note_type"] or "general",
                pinned=bool(r["pinned"]),
                visibility=r["visibility"] or "team",
                task_id=r["task_id"],
                source_activity_id=r["source_activity_id"],
                deleted_at=r["deleted_at"],
            )
            for r in rows
        ]

    def update_note(self, note_id: str, body: str, note_type: str = "general",
                    pinned: bool = False, visibility: str = "team") -> None:
        self._db.conn.execute(self._SQL_UPDATE, (body, note_type, 1 if pinned else 0, visibility, note_id))

    def soft_delete_note(self, note_id: str) -> None:
        self._db.conn.execute(self._SQL_SOFT_DELETE, (note_id,))
