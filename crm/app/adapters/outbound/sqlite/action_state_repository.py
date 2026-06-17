"""action_state_repository.py — write adapter for crm_action_state.

crm_action_state holds employee-set lifecycle status for warehouse action_queue items
(dismiss / snooze). Keyed on action_id; auto-expires when a new episode starts.
Writes to crm.db (the writable side); cache.db is read-only and never written here.
"""

from __future__ import annotations

import sqlite3
from typing import Optional


class SQLiteActionStateRepository:
    """Write adapter for crm_action_state in crm.db."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def dismiss(self, action_id: str, user_id: Optional[str] = None) -> None:
        sql = (
            "INSERT INTO crm_action_state (action_id, status, updated_by) "
            "VALUES (?, 'dismissed', ?) "
            "ON CONFLICT(action_id) DO UPDATE SET "
            "  status = 'dismissed', "
            "  snoozed_until = NULL, "
            "  updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
            "  updated_by = excluded.updated_by"
        )
        with self._conn:
            self._conn.execute(sql, (action_id, user_id))

    def snooze(self, action_id: str, until_date: str, user_id: Optional[str] = None) -> None:
        sql = (
            "INSERT INTO crm_action_state (action_id, status, snoozed_until, updated_by) "
            "VALUES (?, 'snoozed', ?, ?) "
            "ON CONFLICT(action_id) DO UPDATE SET "
            "  status = 'snoozed', "
            "  snoozed_until = excluded.snoozed_until, "
            "  updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
            "  updated_by = excluded.updated_by"
        )
        with self._conn:
            self._conn.execute(sql, (action_id, until_date, user_id))

    def reopen(self, action_id: str) -> None:
        """Reset to open (undo a dismiss or snooze)."""
        sql = (
            "UPDATE crm_action_state "
            "SET status = 'open', snoozed_until = NULL, "
            "    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
            "WHERE action_id = ?"
        )
        with self._conn:
            self._conn.execute(sql, (action_id,))
