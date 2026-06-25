"""test_cache_repository_customer_id.py — Integration tests for customer_id in list_all_action_queue.

Verifies that ActionQueueItem.customer_id is populated from wh_customer_base (via
wh_action_queue.customer_key JOIN) and is None when no matching base row exists.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase          # noqa: E402
from crm.src.adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_cache_tables(cache_conn: sqlite3.Connection) -> None:
    """Create minimal cache tables needed by list_all_action_queue."""
    cache_conn.executescript("""
        CREATE TABLE IF NOT EXISTS wh_customer_base (
            customer_key  TEXT PRIMARY KEY,
            customer_id   INTEGER,
            display_name  TEXT
        );

        CREATE TABLE IF NOT EXISTS wh_action_queue (
            action_id          TEXT PRIMARY KEY,
            customer_key       TEXT,
            action_type        TEXT,
            rationale_vi       TEXT,
            value_at_stake_vnd INTEGER,
            priority           INTEGER,
            generated_date     TEXT,
            pending_since      TEXT,
            refreshed_at       TEXT,
            top_affinity_product    TEXT,
            last_purchased_product  TEXT
        );

        CREATE TABLE IF NOT EXISTS wh_party_seed (
            customer_key  TEXT PRIMARY KEY,
            customer_id   INTEGER
        );
    """)
    cache_conn.commit()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_list_all_action_queue_customer_id_present():
    """ActionQueueItem.customer_id is populated when wh_customer_base has a row."""
    with tempfile.TemporaryDirectory() as d:
        db = CRMDatabase(d)
        db.apply_migrations()

        cache_path = str(pathlib.Path(d) / "cache.db")
        cache_conn = sqlite3.connect(cache_path)
        try:
            _setup_cache_tables(cache_conn)

            # Insert a customer base row linking customer_key → customer_id.
            cache_conn.execute(
                "INSERT INTO wh_customer_base VALUES ('ck-abc', 603264280, 'Nguyen Van A')"
            )
            # Insert an action referencing that customer_key.
            cache_conn.execute("""
                INSERT INTO wh_action_queue VALUES
                ('aq-001', 'ck-abc', 'CALL_NOW', 'Test rationale',
                 1000000, 1, '2026-06-25', '2026-06-24', '2026-06-25T00:00:00Z',
                 'Cordyceps', 'Fucoidan')
            """)
            cache_conn.commit()
        finally:
            cache_conn.close()

        repo = SQLiteCacheRepository(db.conn)
        items = repo.list_all_action_queue()

        db.close()

    assert len(items) == 1
    assert items[0].customer_id == 603264280


def test_list_all_action_queue_customer_id_none_when_no_base_row():
    """ActionQueueItem.customer_id is None when customer_key has no wh_customer_base row."""
    with tempfile.TemporaryDirectory() as d:
        db = CRMDatabase(d)
        db.apply_migrations()

        cache_path = str(pathlib.Path(d) / "cache.db")
        cache_conn = sqlite3.connect(cache_path)
        try:
            _setup_cache_tables(cache_conn)

            # No wh_customer_base row — orphan action.
            cache_conn.execute("""
                INSERT INTO wh_action_queue VALUES
                ('aq-002', 'ck-unknown', 'WIN_BACK', 'No base row',
                 500000, 2, '2026-06-25', '2026-06-24', '2026-06-25T00:00:00Z',
                 '', '')
            """)
            cache_conn.commit()
        finally:
            cache_conn.close()

        repo = SQLiteCacheRepository(db.conn)
        items = repo.list_all_action_queue()

        db.close()

    assert len(items) == 1
    assert items[0].customer_id is None
