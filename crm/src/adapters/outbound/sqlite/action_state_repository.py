"""action_state_repository.py — write adapter for crm_action_state + crm_action_dismissal.

crm_action_state holds employee-set lifecycle status for warehouse action_queue items
(dismiss / snooze). Keyed on action_id; auto-expires when a new episode starts.

crm_action_dismissal (B5, added migration 0038) holds the longer-lived dismiss memory
keyed on (party_id, action_type) with a 30-day TTL — survives the warehouse regenerating
a new action_id for the same semantic action across weekly refreshes, which the
action_id-keyed crm_action_state cannot. dismiss() writes BOTH tables: crm_action_state
still marks this exact action_id's status for the current episode (read by
SQLiteCacheRepository._fetch_actions for the C360 reason rail), while crm_action_dismissal
is the cross-episode memory the worklist query filters on (SQLiteCacheRepository.
list_all_action_queue). Resolving party_id/action_type from action_id requires reading
cache.wh_action_queue / wh_sku_action_queue — both DBs are ATTACHed to the same
connection (see connection.py), so this adapter reads cache.* here despite the
"writes to crm.db" framing; it never writes to cache.db.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.action_dismissal import ActionDismissal

_DISMISSAL_TTL_DAYS = 30


def _is_missing_table_or_column(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "no such table" in msg or "no such column" in msg


class SQLiteActionStateRepository:
    """Write adapter for crm_action_state + crm_action_dismissal in crm.db."""

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
        self._dismiss_by_party_and_type(action_id, user_id)

    # ── B5: (party_id, action_type) TTL dismissal ─────────────────────────────

    def _dismiss_by_party_and_type(self, action_id: str, user_id: Optional[str]) -> None:
        """Best-effort: resolve action_id → (party_id, action_type, source_mart) and
        upsert the cross-episode dismissal row. Silently skipped (not raised) when the
        action can no longer be resolved (stale/removed from cache, or party not yet
        linked) — the per-episode crm_action_state write above already succeeded
        and remains the source of truth for that case.
        """
        resolved = self._resolve_party_and_action_type(action_id)
        if resolved is None:
            return
        party_id, action_type, source_mart = resolved
        sql = (
            "INSERT INTO crm_action_dismissal "
            "  (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until) "
            "VALUES (?, ?, ?, ?, "
            "        strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
            f"        strftime('%Y-%m-%dT%H:%M:%fZ','now','+{_DISMISSAL_TTL_DAYS} days')) "
            "ON CONFLICT(party_id, action_type, source_mart) DO UPDATE SET "
            "  dismissed_by_user_id = excluded.dismissed_by_user_id, "
            "  dismissed_at = excluded.dismissed_at, "
            "  dismissed_until = excluded.dismissed_until"
        )
        with self._conn:
            self._conn.execute(sql, (party_id, action_type, source_mart, user_id))

    def _resolve_party_and_action_type(self, action_id: str) -> Optional[tuple[str, str, str]]:
        """Look up (party_id, action_type, source_mart) for action_id via the same
        cache-join pattern as SQLiteCacheRepository.list_all_action_queue(). Checks the
        customer-level branch first, then the SKU-level branch — whichever branch
        matches tells us the originating mart, at zero extra query cost. Returns None
        when the action_id is not found in either, or its party_id has not been
        resolved yet (customer not linked to a CRM party) — dismissal memory is
        scoped by party_id, so there is nothing meaningful to key it on.
        """
        branches = (
            ("mart_customer_action_queue", """
            SELECT a.action_type AS action_type, pi.party_id AS party_id
            FROM cache.wh_action_queue a
            LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = a.customer_key
            LEFT JOIN crm_party_identity pi
                   ON pi.identity_type = 'sapo_customer'
                  AND pi.identity_value = CAST(ps.customer_id AS TEXT)
            WHERE a.action_id = ?
            """),
            ("mart_customer_sku_action_queue", """
            SELECT sa.action_type AS action_type, pi.party_id AS party_id
            FROM cache.wh_sku_action_queue sa
            LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = sa.customer_key
            LEFT JOIN crm_party_identity pi
                   ON pi.identity_type = 'sapo_customer'
                  AND pi.identity_value = CAST(ps.customer_id AS TEXT)
            WHERE sa.action_id = ?
            """),
        )
        for source_mart, sql in branches:
            try:
                row = self._conn.execute(sql, (action_id,)).fetchone()
            except sqlite3.OperationalError as exc:
                if _is_missing_table_or_column(exc):
                    continue
                raise
            if row and row["party_id"] and row["action_type"]:
                return (row["party_id"], row["action_type"], source_mart)
        return None

    # ── Suggestion Settings panel: direct, pre-emptive suppression ───────────

    def suppress(self, party_id: str, action_type: str, source_mart: str,
                 until_utc: str, user_id: Optional[str] = None) -> None:
        """Turn an opportunity type off for a party, effective until `until_utc`
        (a bound UTC ISO-8601 string — never f-string interpolated). Unlike
        `_dismiss_by_party_and_type`, this does NOT require an active `action_id` —
        the panel can suppress a type before it has ever fired for this party.
        Upsert: re-suppressing overwrites the end date and the acting user.
        """
        sql = (
            "INSERT INTO crm_action_dismissal "
            "  (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until) "
            "VALUES (?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?) "
            "ON CONFLICT(party_id, action_type, source_mart) DO UPDATE SET "
            "  dismissed_by_user_id = excluded.dismissed_by_user_id, "
            "  dismissed_at = excluded.dismissed_at, "
            "  dismissed_until = excluded.dismissed_until"
        )
        with self._conn:
            self._conn.execute(sql, (party_id, action_type, source_mart, user_id, until_utc))

    def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None:
        """Turn a suggestion back on — deletes the suppression row outright."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM crm_action_dismissal "
                "WHERE party_id = ? AND action_type = ? AND source_mart = ?",
                (party_id, action_type, source_mart),
            )

    def list_dismissals_for_party(self, party_id: str) -> list[ActionDismissal]:
        """Return ALL dismissal rows for one party, including expired ones — the
        panel needs to distinguish "đã hết hạn" from "đang bật" rather than have
        expired rows silently vanish. Returns [] when the table is absent
        (pre-migration) rather than raising."""
        sql = """
            SELECT d.party_id, d.action_type, d.source_mart, d.dismissed_by_user_id,
                   d.dismissed_at, d.dismissed_until,
                   p.display_name, p.primary_phone,
                   u.full_name AS dismissed_by_name
            FROM crm_action_dismissal d
            LEFT JOIN crm_party p ON p.party_id = d.party_id
            LEFT JOIN crm_app_user u ON u.user_id = d.dismissed_by_user_id
            WHERE d.party_id = ?
            ORDER BY d.action_type, d.source_mart
        """
        try:
            rows = self._conn.execute(sql, (party_id,)).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table_or_column(exc):
                return []
            raise
        return [self._row_to_dismissal(row) for row in rows]

    def list_active_dismissals(self) -> list[ActionDismissal]:
        """Return non-expired (party_id, action_type) dismissals for the manager
        transparency view (AI-11), newest first. Enriches each row with a display
        name (party display_name → primary_phone → placeholder, matching
        TaskService._customer_fallback_label) and the dismissing user's name so
        the template needs no further lookups. Returns [] when the table is absent
        (pre-migration) rather than raising.
        """
        sql = """
            SELECT d.party_id, d.action_type, d.source_mart, d.dismissed_by_user_id,
                   d.dismissed_at, d.dismissed_until,
                   p.display_name, p.primary_phone,
                   u.full_name AS dismissed_by_name
            FROM crm_action_dismissal d
            LEFT JOIN crm_party p ON p.party_id = d.party_id
            LEFT JOIN crm_app_user u ON u.user_id = d.dismissed_by_user_id
            WHERE d.dismissed_until > strftime('%Y-%m-%dT%H:%M:%fZ','now')
            ORDER BY d.dismissed_at DESC
        """
        try:
            rows = self._conn.execute(sql).fetchall()
        except sqlite3.OperationalError as exc:
            if _is_missing_table_or_column(exc):
                return []
            raise
        return [self._row_to_dismissal(row) for row in rows]

    @staticmethod
    def _row_to_dismissal(row: sqlite3.Row) -> ActionDismissal:
        return ActionDismissal(
            party_id=row["party_id"],
            action_type=row["action_type"],
            source_mart=row["source_mart"],
            dismissed_by_user_id=row["dismissed_by_user_id"],
            dismissed_at=row["dismissed_at"] or "",
            dismissed_until=row["dismissed_until"] or "",
            party_display=(row["display_name"] or row["primary_phone"] or "(chưa xác định)"),
            dismissed_by_display=row["dismissed_by_name"] or "Hệ thống",
        )

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

    def resolve_party_id(self, action_id: str) -> Optional[str]:
        """Phase-03 IDOR fix: expose party_id resolution as a port method so
        bulk-resolve callers can verify an action_id genuinely belongs to the
        party they claim before dismiss()/snooze() mutates it. Thin wrapper —
        reuses _resolve_party_and_action_type() verbatim (same cache-join
        lookup dismiss() already depends on for its own TTL-dismissal write),
        no duplicated SQL. Returns None when unresolvable."""
        resolved = self._resolve_party_and_action_type(action_id)
        return resolved[0] if resolved else None
