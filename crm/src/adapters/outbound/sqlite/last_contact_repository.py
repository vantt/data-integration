"""SQLite adapter — crm_last_contact table (one row per customer)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from crm.src.domain.entities.last_contact import LastContact
from crm.src.adapters.outbound.sqlite.connection import CRMDatabase

_UPSERT = """
INSERT INTO crm_last_contact (
  party_id, last_activity_id, last_contacted_at, last_contact_result, channel, updated_at
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT (party_id) DO UPDATE SET
  last_activity_id    = excluded.last_activity_id,
  last_contacted_at   = excluded.last_contacted_at,
  last_contact_result = excluded.last_contact_result,
  channel             = excluded.channel,
  updated_at          = excluded.updated_at
WHERE excluded.last_contacted_at >= crm_last_contact.last_contacted_at
"""

_GET = """
SELECT party_id, last_activity_id, last_contacted_at, last_contact_result, channel, updated_at
FROM crm_last_contact WHERE party_id = ?
"""

_GET_MANY = """
SELECT party_id, last_activity_id, last_contacted_at, last_contact_result, channel, updated_at
FROM crm_last_contact WHERE party_id IN ({placeholders})
"""


def _row_to_entity(row: sqlite3.Row) -> LastContact:
    return LastContact(
        party_id=row["party_id"],
        last_activity_id=row["last_activity_id"],
        last_contacted_at=row["last_contacted_at"],
        last_contact_result=row["last_contact_result"],
        channel=row["channel"],
        updated_at=row["updated_at"],
    )


class SQLiteLastContactRepository:
    def __init__(self, db: CRMDatabase) -> None:
        self._conn = db.conn

    def upsert(
        self,
        party_id: str,
        activity_id: str,
        contacted_at: str,
        result: str,
        channel: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(_UPSERT, (party_id, activity_id, contacted_at, result, channel, now))
        self._conn.commit()

    def get_by_party(self, party_id: str) -> Optional[LastContact]:
        row = self._conn.execute(_GET, (party_id,)).fetchone()
        return _row_to_entity(row) if row else None

    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]:
        """Return {party_id: LastContact} for all given party_ids in one query."""
        if not party_ids:
            return {}
        placeholders = ",".join("?" * len(party_ids))
        sql = _GET_MANY.format(placeholders=placeholders)
        rows = self._conn.execute(sql, party_ids).fetchall()
        return {row["party_id"]: _row_to_entity(row) for row in rows}
