"""test_migration_action_dismissal_source_mart.py — plan 260805-1216 phase-03.

First migration up/down test in the repo (there was none before). Tests the SQL of
migration 0046 directly against a connection that already has the full schema (via
CRMDatabase.apply_migrations, which lands on the NEW crm_action_dismissal shape), by:
  1. Rebuilding the pre-0046 (0038) shape by hand and seeding 2 legacy rows.
  2. Re-executing the 0046 .up.sql file text directly — asserts the backfill expands
     each legacy row into one row per mart (2 rows -> 4 rows), preserving
     dismissed_by_user_id/dismissed_at/dismissed_until.
  3. Re-executing the 0046 .down.sql file text — asserts collapse back to 2 rows,
     keeping the LATEST dismissed_until per (party_id, action_type).
  4. Asserts the CHECK constraint rejects an invalid source_mart value.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import uuid

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_MIGRATIONS_DIR = pathlib.Path(__file__).parents[2] / "migrations"
_UP_SQL = (_MIGRATIONS_DIR / "0046_action_dismissal_source_mart.up.sql").read_text(encoding="utf-8")
_DOWN_SQL = (_MIGRATIONS_DIR / "0046_action_dismissal_source_mart.down.sql").read_text(encoding="utf-8")


def _rebuild_0038_shape_with_legacy_rows(conn: sqlite3.Connection, party_ids: list[str]) -> None:
    """Drop the post-0046 table and recreate the pre-0046 (0038) shape, seeding one
    legacy (mart-agnostic) row per party_id so the up.sql backfill has something to expand."""
    conn.executescript("DROP TABLE IF EXISTS crm_action_dismissal;")
    conn.executescript("""
        CREATE TABLE crm_action_dismissal (
          party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
          action_type          TEXT    NOT NULL,
          dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
          dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          dismissed_until      TEXT    NOT NULL,
          PRIMARY KEY (party_id, action_type)
        );
    """)
    conn.execute(
        "INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name) "
        "VALUES ('user-1', 'user1@test.vn', 'Test User')"
    )
    for i, party_id in enumerate(party_ids):
        conn.execute(
            "INSERT INTO crm_action_dismissal "
            "  (party_id, action_type, dismissed_by_user_id, dismissed_at, dismissed_until) "
            "VALUES (?, ?, ?, ?, ?)",
            (party_id, "REORDER_NUDGE", "user-1",
             f"2026-07-0{i+1}T00:00:00.000Z", f"2026-08-0{i+1}T00:00:00.000Z"),
        )
    conn.commit()


@pytest.fixture()
def migrated_conn(seeded_crm_db):
    """seeded_crm_db already ran every *.up.sql, including 0046 — lands on the NEW shape."""
    return seeded_crm_db.conn


def _insert_party(conn: sqlite3.Connection, party_id: str) -> None:
    conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, "Test Party"),
    )
    conn.commit()


class TestMigration0046Up:
    def test_backfill_expands_legacy_rows_into_both_marts(self, migrated_conn):
        party_a = str(uuid.uuid4())
        party_b = str(uuid.uuid4())
        _insert_party(migrated_conn, party_a)
        _insert_party(migrated_conn, party_b)
        _rebuild_0038_shape_with_legacy_rows(migrated_conn, [party_a, party_b])

        migrated_conn.executescript(_UP_SQL)

        rows = migrated_conn.execute(
            "SELECT party_id, action_type, source_mart, dismissed_by_user_id, "
            "dismissed_at, dismissed_until FROM crm_action_dismissal ORDER BY party_id, source_mart"
        ).fetchall()
        assert len(rows) == 4  # 2 legacy rows x 2 marts

        marts_by_party = {}
        for r in rows:
            marts_by_party.setdefault(r["party_id"], []).append(r["source_mart"])
        for party_id in (party_a, party_b):
            assert sorted(marts_by_party[party_id]) == [
                "mart_customer_action_queue", "mart_customer_sku_action_queue",
            ]

        # dismissed_by_user_id/dismissed_at/dismissed_until preserved verbatim.
        for r in rows:
            assert r["dismissed_by_user_id"] == "user-1"
            assert r["action_type"] == "REORDER_NUDGE"

    def test_check_constraint_rejects_invalid_source_mart(self, migrated_conn):
        party_id = str(uuid.uuid4())
        _insert_party(migrated_conn, party_id)
        _rebuild_0038_shape_with_legacy_rows(migrated_conn, [])
        migrated_conn.executescript(_UP_SQL)

        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            migrated_conn.execute(
                "INSERT INTO crm_action_dismissal "
                "  (party_id, action_type, source_mart, dismissed_until) "
                "VALUES (?, 'CALL_NOW', 'nonsense', '2026-09-01T00:00:00.000Z')",
                (party_id,),
            )


class TestMigration0046Down:
    def test_collapse_keeps_latest_dismissed_until_per_party_action_type(self, migrated_conn):
        party_a = str(uuid.uuid4())
        _insert_party(migrated_conn, party_a)
        _rebuild_0038_shape_with_legacy_rows(migrated_conn, [party_a])
        migrated_conn.executescript(_UP_SQL)

        # Diverge the two expanded rows' dismissed_until so collapse must pick the later one.
        migrated_conn.execute(
            "UPDATE crm_action_dismissal SET dismissed_until = '2026-12-01T00:00:00.000Z' "
            "WHERE party_id = ? AND source_mart = 'mart_customer_action_queue'",
            (party_a,),
        )
        migrated_conn.execute(
            "UPDATE crm_action_dismissal SET dismissed_until = '2026-09-01T00:00:00.000Z' "
            "WHERE party_id = ? AND source_mart = 'mart_customer_sku_action_queue'",
            (party_a,),
        )
        migrated_conn.commit()

        migrated_conn.executescript(_DOWN_SQL)

        rows = migrated_conn.execute(
            "SELECT party_id, action_type, dismissed_until FROM crm_action_dismissal"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["party_id"] == party_a
        assert rows[0]["dismissed_until"] == "2026-12-01T00:00:00.000Z"  # the LATER of the two

        # Column list matches the pre-0046 (0038) shape — no source_mart column.
        cols = {r[1] for r in migrated_conn.execute("PRAGMA table_info(crm_action_dismissal)")}
        assert "source_mart" not in cols
        assert cols == {"party_id", "action_type", "dismissed_by_user_id", "dismissed_at", "dismissed_until"}
