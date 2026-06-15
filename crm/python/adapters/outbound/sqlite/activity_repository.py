"""SQLite adapter implementing ActivityRepository port for CRM.

Mirrors Go adapter (activity_repo.go) — exact same SQL.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from crm.python.domain.entities.activity import Activity
from crm.python.adapters.outbound.sqlite.connection import CRMDatabase

# ---------------------------------------------------------------------------
# SQL (ported verbatim from activity_queries.sql)
# ---------------------------------------------------------------------------

_INSERT = """
INSERT INTO crm_activity (
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_LIST_BY_PARTY = """
SELECT
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at
FROM crm_activity
WHERE party_id = ?
ORDER BY occurred_at DESC
LIMIT ?
"""


# ---------------------------------------------------------------------------
# Row mapper
# ---------------------------------------------------------------------------

def _activity_from_row(row: sqlite3.Row) -> Activity:
    return Activity(
        activity_id=row["activity_id"],
        party_id=row["party_id"],
        activity_type=row["activity_type"],
        occurred_at=row["occurred_at"],
        created_at=row["created_at"],
        direction=row["direction"],
        channel=row["channel"],
        subject=row["subject"],
        body=row["body"],
        outcome=row["outcome"],
        related_order_code=row["related_order_code"],
        staff_user_id=row["staff_user_id"],
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteActivityRepository:
    """SQLite implementation of ActivityRepository.

    Duck-typed against domain.ports.activity_repository.ActivityRepository.
    """

    def __init__(self, db: CRMDatabase) -> None:
        self._conn = db.conn

    def insert(self, activity: Activity) -> Activity:
        """Store a new activity row and return the activity."""
        self._conn.execute(_INSERT, (
            activity.activity_id,
            activity.party_id,
            activity.activity_type,
            activity.direction,
            activity.channel,
            activity.subject,
            activity.body,
            activity.outcome,
            activity.related_order_code,
            activity.staff_user_id,
            activity.occurred_at,
            activity.created_at,
        ))
        self._conn.commit()
        return activity

    def list_by_party(self, party_id: str, limit: int = 50) -> list[Activity]:
        """Return activities for a party ordered by occurred_at DESC (newest first)."""
        rows = self._conn.execute(_LIST_BY_PARTY, (party_id, limit)).fetchall()
        return [_activity_from_row(r) for r in rows]
