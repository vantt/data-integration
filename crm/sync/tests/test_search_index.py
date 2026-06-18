"""test_search_index.py — unit tests for crm/sync/search_index.py rebuild logic."""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from crm.sync.search_index import rebuild_search_index  # noqa: E402


def _make_crm_db(path: str) -> None:
    """Minimal crm.db with crm_party, crm_party_identity, crm_party_search."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE crm_party (
            party_id TEXT PRIMARY KEY,
            display_name TEXT
        );
        CREATE TABLE crm_party_identity (
            identity_id TEXT PRIMARY KEY,
            party_id TEXT,
            identity_type TEXT,
            identity_value TEXT,
            contact_status TEXT DEFAULT 'active'
        );
        CREATE VIRTUAL TABLE crm_party_search USING fts5(
            party_id UNINDEXED,
            tokens,
            tokenize = "unicode61 remove_diacritics 2 tokenchars '@.'"
        );
    """)
    conn.commit()
    conn.close()


def _make_cache_db(path: str) -> None:
    """Minimal cache.db with wh_order_hdr."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE wh_order_hdr (
            order_id INTEGER,
            order_code TEXT,
            customer_id INTEGER
        );
    """)
    conn.commit()
    conn.close()


def _insert_party(crm_path: str, party_id: str, display_name: str, identities: list) -> None:
    conn = sqlite3.connect(crm_path)
    conn.execute("INSERT INTO crm_party VALUES (?, ?)", (party_id, display_name))
    for i, (itype, ival, status) in enumerate(identities):
        conn.execute(
            "INSERT INTO crm_party_identity VALUES (?, ?, ?, ?, ?)",
            (f"{party_id}-i{i}", party_id, itype, ival, status)
        )
    conn.commit()
    conn.close()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_rebuild_indexes_basic_party():
    with tempfile.TemporaryDirectory() as tmp:
        crm = tmp + "/crm.db"
        cache = tmp + "/cache.db"
        _make_crm_db(crm)
        _make_cache_db(cache)
        _insert_party(crm, "p-001", "Nguyen Van A", [
            ("phone", "0901000001", "active"),
            ("email", "a@test.vn", "active"),
        ])
        count = rebuild_search_index(crm, cache)
        assert count == 1
        conn = sqlite3.connect(crm)
        rows = conn.execute("SELECT tokens FROM crm_party_search").fetchall()
        conn.close()
        assert len(rows) == 1
        tokens = rows[0][0]
        assert "Nguyen Van A" in tokens
        assert "0901000001" in tokens
        assert "a@test.vn" in tokens


def test_rebuild_skips_invalid_identities():
    with tempfile.TemporaryDirectory() as tmp:
        crm = tmp + "/crm.db"
        cache = tmp + "/cache.db"
        _make_crm_db(crm)
        _make_cache_db(cache)
        _insert_party(crm, "p-002", "Tran Thi B", [
            ("phone", "0909111222", "active"),
            ("phone", "+84909999999", "invalid"),  # should be skipped
        ])
        rebuild_search_index(crm, cache)
        conn = sqlite3.connect(crm)
        tokens = conn.execute("SELECT tokens FROM crm_party_search").fetchone()[0]
        conn.close()
        assert "+84909999999" not in tokens
        assert "0909" in tokens  # the active phone is there


def test_rebuild_indexes_order_codes():
    with tempfile.TemporaryDirectory() as tmp:
        crm = tmp + "/crm.db"
        cache = tmp + "/cache.db"
        _make_crm_db(crm)
        _make_cache_db(cache)
        _insert_party(crm, "p-003", "Le Van C", [
            ("sapo_customer", "1001", "active"),
        ])
        # Add order to cache.db
        conn = sqlite3.connect(cache)
        conn.execute("INSERT INTO wh_order_hdr VALUES (?, ?, ?)", (5001, "DH-001", 1001))
        conn.commit()
        conn.close()
        rebuild_search_index(crm, cache)
        conn = sqlite3.connect(crm)
        tokens = conn.execute("SELECT tokens FROM crm_party_search WHERE party_id='p-003'").fetchone()[0]
        conn.close()
        assert "DH-001" in tokens
        assert "5001" in tokens


def test_rebuild_skips_null_customer_id_orders():
    with tempfile.TemporaryDirectory() as tmp:
        crm = tmp + "/crm.db"
        cache = tmp + "/cache.db"
        _make_crm_db(crm)
        _make_cache_db(cache)
        _insert_party(crm, "p-004", "Guest Order Test", [])
        # Guest order: customer_id is NULL
        conn = sqlite3.connect(cache)
        conn.execute("INSERT INTO wh_order_hdr VALUES (?, ?, ?)", (9999, "DH-GUEST", None))
        conn.commit()
        conn.close()
        count = rebuild_search_index(crm, cache)
        # Party with no identities and no name tokens — verify DH-GUEST not linked to p-004
        conn = sqlite3.connect(crm)
        row = conn.execute("SELECT tokens FROM crm_party_search WHERE party_id='p-004'").fetchone()
        conn.close()
        if row:
            assert "DH-GUEST" not in row[0]


def test_rebuild_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        crm = tmp + "/crm.db"
        cache = tmp + "/cache.db"
        _make_crm_db(crm)
        _make_cache_db(cache)
        _insert_party(crm, "p-005", "Idempotent Test", [
            ("phone", "0901234567", "active"),
        ])
        rebuild_search_index(crm, cache)
        rebuild_search_index(crm, cache)  # second run
        conn = sqlite3.connect(crm)
        count = conn.execute("SELECT COUNT(*) FROM crm_party_search").fetchone()[0]
        conn.close()
        assert count == 1  # not doubled
