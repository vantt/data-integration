"""SQLite adapters for Tag, PartyTag, and Note entities.

Implements ports.TagRepository and ports.NoteRepository using raw sqlite3
queries ported from tag_queries.sql and note_queries.sql (Go sqlc source).
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase
from crm.src.domain.entities.profile import Note, PartyTag, Tag


# ---------------------------------------------------------------------------
# SQLiteTagRepository
# ---------------------------------------------------------------------------

class SQLiteTagRepository:
    """Implements TagRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── SQL (ported from tag_queries.sql) ─────────────────────────────────────

    _SQL_LIST_ALL = """
        SELECT tag_id, name, category, color
        FROM crm_tag
        ORDER BY category, name
    """

    _SQL_LIST_BY_CATEGORY = """
        SELECT tag_id, name, category, color
        FROM crm_tag
        WHERE category = ?
        ORDER BY name
    """

    _SQL_GET = """
        SELECT tag_id, name, category, color
        FROM crm_tag
        WHERE tag_id = ?
        LIMIT 1
    """

    _SQL_CREATE = """
        INSERT INTO crm_tag (tag_id, name, category, color)
        VALUES (?, ?, ?, ?)
    """

    _SQL_ATTACH = """
        INSERT OR IGNORE INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at)
        VALUES (?, ?, ?, ?)
    """

    _SQL_DETACH = """
        DELETE FROM crm_party_tag
        WHERE party_id = ? AND tag_id = ?
    """

    _SQL_LIST_PARTY_TAGS = """
        SELECT t.tag_id, t.name, t.category, t.color
        FROM crm_tag t
        JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
        WHERE pt.party_id = ?
        ORDER BY t.category, t.name
    """

    _SQL_LIST_PARTY_TAGS_WITH_META = """
        SELECT t.tag_id, t.name, t.category, t.color,
               pt.tagged_by, pt.tagged_at
        FROM crm_tag t
        JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
        WHERE pt.party_id = ?
        ORDER BY t.category, t.name
    """

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_tag(row: sqlite3.Row) -> Tag:
        return Tag(
            tag_id=row["tag_id"],
            name=row["name"],
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

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        row = self._db.conn.execute(self._SQL_GET, (tag_id,)).fetchone()
        return self._row_to_tag(row) if row else None

    def create_tag(self, tag: Tag) -> None:
        self._db.conn.execute(self._SQL_CREATE, (tag.tag_id, tag.name, tag.category, tag.color))
        self._db.conn.commit()

    def attach_tag(self, party_id: str, tag_id: str, user_id: Optional[str], tagged_at: str) -> None:
        """INSERT OR IGNORE — idempotent on duplicate (party_id, tag_id)."""
        self._db.conn.execute(self._SQL_ATTACH, (party_id, tag_id, user_id, tagged_at))
        self._db.conn.commit()

    def attach_party_tag(self, party_tag: PartyTag) -> None:
        """Convenience overload accepting a PartyTag dataclass."""
        self.attach_tag(
            party_id=party_tag.party_id,
            tag_id=party_tag.tag_id,
            user_id=party_tag.tagged_by,
            tagged_at=party_tag.tagged_at,
        )

    def detach_tag(self, party_id: str, tag_id: str) -> None:
        self._db.conn.execute(self._SQL_DETACH, (party_id, tag_id))
        self._db.conn.commit()

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
                category=r["category"],
                color=r["color"],
                tagged_by=r["tagged_by"],
                tagged_at=r["tagged_at"],
            )
            for r in rows
        ]


# ---------------------------------------------------------------------------
# SQLiteNoteRepository
# ---------------------------------------------------------------------------

class SQLiteNoteRepository:
    """Implements NoteRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── SQL (ported from note_queries.sql) ────────────────────────────────────

    _SQL_INSERT = """
        INSERT INTO crm_note (note_id, party_id, body, author_user_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    """

    _SQL_LIST = """
        SELECT note_id, party_id, body, author_user_id, created_at
        FROM crm_note
        WHERE party_id = ?
        ORDER BY created_at DESC
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def add_note(self, note: Note) -> None:
        self._db.conn.execute(self._SQL_INSERT, (
            note.note_id,
            note.party_id,
            note.body,
            note.author_user_id,
            note.created_at,
        ))
        self._db.conn.commit()

    def list_notes(self, party_id: str, limit: int = 50) -> list[Note]:
        rows = self._db.conn.execute(self._SQL_LIST, (party_id,)).fetchmany(limit)
        return [
            Note(
                note_id=r["note_id"],
                party_id=r["party_id"],
                body=r["body"],
                author_user_id=r["author_user_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
