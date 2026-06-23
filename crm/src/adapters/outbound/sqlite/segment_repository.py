"""SQLiteSegmentRepository — SQLite adapter for Segment and SegmentMember persistence.

Mirrors Go segment_repo.go / segment_queries.sql exactly.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from domain.entities.segment import Segment, SegmentMember


class SQLiteSegmentRepository:
    """SQLite adapter implementing the SegmentRepository port."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Segment CRUD ──────────────────────────────────────────────────────────

    def insert(self, segment: Segment) -> None:
        """INSERT a new segment row."""
        definition = json.dumps(segment.definition) if segment.definition is not None else None
        self._conn.execute(
            """
            INSERT INTO crm_segment (
              segment_id, name, description, is_dynamic, definition, owner_user_id,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                segment.segment_id,
                segment.name,
                segment.description,
                1 if segment.is_dynamic else 0,
                definition,
                segment.owner_user_id,
                segment.created_at,
                segment.updated_at,
            ),
        )
        self._conn.commit()

    def get_by_id(self, segment_id: str) -> Optional[Segment]:
        """Return a segment by PK, or None if not found."""
        row = self._conn.execute(
            """
            SELECT segment_id, name, description, is_dynamic, definition,
                   owner_user_id, created_at, updated_at
            FROM crm_segment
            WHERE segment_id = ?
            """,
            (segment_id,),
        ).fetchone()
        if row is None:
            return None
        return self._segment_from_row(row)

    def update(self, segment: Segment) -> None:
        """Persist mutable segment fields (name, description, is_dynamic, definition, owner_user_id)."""
        definition = json.dumps(segment.definition) if segment.definition is not None else None
        self._conn.execute(
            """
            UPDATE crm_segment
            SET name          = ?,
                description   = ?,
                is_dynamic    = ?,
                definition    = ?,
                owner_user_id = ?,
                updated_at    = ?
            WHERE segment_id = ?
            """,
            (
                segment.name,
                segment.description,
                1 if segment.is_dynamic else 0,
                definition,
                segment.owner_user_id,
                segment.updated_at,
                segment.segment_id,
            ),
        )
        self._conn.commit()

    def list(self) -> list[Segment]:
        """Return all segments ordered by created_at DESC (port contract name)."""
        return self.list_segments()

    def list_segments(self) -> list[Segment]:
        """Return all segments ordered by created_at DESC."""
        rows = self._conn.execute(
            """
            SELECT segment_id, name, description, is_dynamic, definition,
                   owner_user_id, created_at, updated_at
            FROM crm_segment
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [self._segment_from_row(r) for r in rows]

    # ── SegmentMember CRUD ────────────────────────────────────────────────────

    def upsert_member(self, member: "SegmentMember") -> None:
        """INSERT or UPDATE a segment member — accepts a SegmentMember object (port contract).

        Manual membership is never overwritten by a rule re-evaluation
        (mirrors the SQL: keep 'manual' source if already set).
        """
        self._conn.execute(
            """
            INSERT INTO crm_segment_member (segment_id, party_id, source, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (segment_id, party_id) DO UPDATE SET
              source   = CASE WHEN crm_segment_member.source = 'manual'
                              THEN 'manual'
                              ELSE excluded.source END,
              added_at = excluded.added_at
            """,
            (member.segment_id, member.party_id, member.source, member.added_at),
        )
        self._conn.commit()

    def delete_member(self, segment_id: str, party_id: str) -> None:
        """Remove a party from a segment."""
        self._conn.execute(
            "DELETE FROM crm_segment_member WHERE segment_id = ? AND party_id = ?",
            (segment_id, party_id),
        )
        self._conn.commit()

    def list_members(self, segment_id: str, limit: int = 500) -> list[SegmentMember]:
        """Return segment members ordered by added_at DESC, capped at limit."""
        rows = self._conn.execute(
            """
            SELECT segment_id, party_id, source, added_at
            FROM crm_segment_member
            WHERE segment_id = ?
            ORDER BY added_at DESC
            LIMIT ?
            """,
            (segment_id, limit),
        ).fetchall()
        return [
            SegmentMember(
                segment_id=r["segment_id"],
                party_id=r["party_id"],
                source=r["source"],
                added_at=r["added_at"],
            )
            for r in rows
        ]

    def delete_rule_members(self, segment_id: str) -> int:
        """Delete all rule-sourced members for a segment; returns count deleted."""
        cur = self._conn.execute(
            "DELETE FROM crm_segment_member WHERE segment_id = ? AND source = 'rule'",
            (segment_id,),
        )
        self._conn.commit()
        return cur.rowcount

    def evaluate_rule(self, rule: dict) -> list[str]:
        """Translate a validated rule dict into SQL and return matching party_ids.

        Pulled from the application layer to keep the hexagonal boundary clean:
        adapters own all SQL; services own only domain logic.

        SECURITY INVARIANT: column names are hard-coded; only values are parameterised.
        """
        from application.segment_service import (  # noqa: PLC0415
            _build_query_no_having,
            _build_query_with_having,
            _is_missing_table_error,
        )
        needs_orders = bool(rule.get("days_since_last_order_gte"))
        needs_insight = bool(
            rule.get("value_group") or rule.get("customer_status") or rule.get("channel_preference")
        )
        if needs_orders:
            query, args = _build_query_with_having(rule, needs_insight)
        else:
            query, args = _build_query_no_having(rule, needs_insight)
        try:
            cur = self._conn.execute(query, args)
        except Exception as exc:
            if _is_missing_table_error(exc):
                return []
            raise
        return [row[0] for row in cur.fetchall()]

    # ── Mapping helper ────────────────────────────────────────────────────────

    @staticmethod
    def _segment_from_row(row: sqlite3.Row) -> Segment:
        definition_raw = row["definition"]
        definition = json.loads(definition_raw) if definition_raw else None
        return Segment(
            segment_id=row["segment_id"],
            name=row["name"],
            is_dynamic=bool(row["is_dynamic"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row["description"],
            definition=definition,
            owner_user_id=row["owner_user_id"],
        )
