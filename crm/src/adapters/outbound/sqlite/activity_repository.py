"""SQLite adapter implementing ActivityRepository port for CRM.

Mirrors Go adapter (activity_repo.go) — exact same SQL.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from domain.entities.activity import Activity
from adapters.outbound.sqlite.connection import CRMDatabase

# ---------------------------------------------------------------------------
# SQL (ported verbatim from activity_queries.sql)
# ---------------------------------------------------------------------------

_INSERT = """
INSERT INTO crm_activity_log (
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at, custom_fields, task_id, channel_type,
  contact_outcome, outcome_reason
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_LIST_BY_PARTY = """
SELECT
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at, custom_fields, task_id, channel_type,
  contact_outcome, outcome_reason
FROM crm_activity_log
WHERE party_id = ?
ORDER BY occurred_at DESC
LIMIT ?
"""

# Suppression (plan 260709-1638 phase-01, câu hỏi mở #5): a party is suppressed
# from the worklist when their MOST RECENT activity (by occurred_at) carries
# outcome_reason='do_not_contact'. Compares the literal string only — does not
# import the enum from domain.entities.activity (kept out of scope here; see
# plan phase-01 for why).  Runtime filter, no schema/party changes — data stays
# intact, only the worklist view hides it.
_LIST_DO_NOT_CONTACT_PARTY_IDS = """
SELECT a.party_id
FROM crm_activity_log a
WHERE a.outcome_reason = 'do_not_contact'
  AND a.occurred_at = (
    SELECT MAX(b.occurred_at) FROM crm_activity_log b WHERE b.party_id = a.party_id
  )
"""


# ---------------------------------------------------------------------------
# Row mapper
# ---------------------------------------------------------------------------

def _activity_from_row(row: sqlite3.Row) -> Activity:
    raw_cf = row["custom_fields"]
    custom_fields = json.loads(raw_cf) if raw_cf else None
    # Use dict-style access with fallback for backward compat with older DB rows
    # that pre-date migration 0035 (contact_outcome/outcome_reason columns absent).
    keys = row.keys()
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
        custom_fields=custom_fields,
        task_id=row["task_id"],
        channel_type=row["channel_type"],
        contact_outcome=row["contact_outcome"] if "contact_outcome" in keys else None,
        outcome_reason=row["outcome_reason"] if "outcome_reason" in keys else None,
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
            json.dumps(activity.custom_fields) if activity.custom_fields else None,
            activity.task_id,
            activity.channel_type,
            activity.contact_outcome,
            activity.outcome_reason,
        ))
        return activity

    def list_by_party(self, party_id: str, limit: int = 50) -> list[Activity]:
        """Return activities for a party ordered by occurred_at DESC (newest first)."""
        rows = self._conn.execute(_LIST_BY_PARTY, (party_id, limit)).fetchall()
        return [_activity_from_row(r) for r in rows]

    def list_do_not_contact_party_ids(self) -> set[str]:
        """Return party_ids whose MOST RECENT activity has outcome_reason='do_not_contact'.

        Used by WorklistQueryService to suppress those parties from the worklist
        (runtime filter — crm_party_tag/crm_party are untouched, data preserved).
        """
        rows = self._conn.execute(_LIST_DO_NOT_CONTACT_PARTY_IDS).fetchall()
        return {row["party_id"] for row in rows}
