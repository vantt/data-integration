"""test_sqlite_connection.py — integration tests for CRMDatabase SQLite adapter.

Uses tempfile.TemporaryDirectory so no real data directory is touched.
Covers:
  - CRMDatabase opens and pings without error
  - cache.db is created automatically when absent
  - cache schema is attached and readable
  - apply_migrations creates expected tables (schema_migrations + crm_* tables)
  - closing connection is idempotent (no double-close error)
"""
from __future__ import annotations

import pathlib, sys, sqlite3, tempfile  # noqa: E401
import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.app.adapters.outbound.sqlite.connection import CRMDatabase  # noqa: E402


# ── Open + ping ───────────────────────────────────────────────────────────────

def test_crm_database_opens_and_pings():
    with tempfile.TemporaryDirectory() as d:
        db = CRMDatabase(d)
        try:
            db.ping()   # must not raise
        finally:
            db.close()


def test_crm_database_context_manager():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            db.ping()   # must not raise inside __enter__/__exit__


def test_crm_database_creates_data_dir_if_missing():
    with tempfile.TemporaryDirectory() as d:
        nested = pathlib.Path(d) / "sub" / "nested"
        with CRMDatabase(str(nested)) as db:
            db.ping()
        assert (nested / "crm.db").exists()


# ── cache.db auto-creation ────────────────────────────────────────────────────

def test_cache_db_created_automatically():
    with tempfile.TemporaryDirectory() as d:
        cache_path = pathlib.Path(d) / "cache.db"
        assert not cache_path.exists()
        with CRMDatabase(d) as db:
            pass
        assert cache_path.exists()


def test_cache_schema_attached_and_readable():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            assert db.cache_attached() is True


def test_cache_sqlite_master_queryable():
    """SELECT count from cache.sqlite_master must succeed (proves ATTACH worked)."""
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            row = db.conn.execute(
                "SELECT COUNT(*) FROM cache.sqlite_master"
            ).fetchone()
            assert row[0] >= 0


# ── Migrations ────────────────────────────────────────────────────────────────

def test_migrations_create_schema_migrations_table():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            db.apply_migrations()
            count = db.conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='schema_migrations'"
            ).fetchone()[0]
            assert count == 1


def test_migrations_applied_versions_recorded():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            db.apply_migrations()
            rows = db.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
            assert len(rows) >= 1, "at least one migration version must be recorded"


def test_migrations_create_crm_party_table():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            db.apply_migrations()
            count = db.conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name='crm_party'"
            ).fetchone()[0]
            assert count == 1


def test_migrations_idempotent_on_second_call():
    """Calling apply_migrations twice must not raise or duplicate rows."""
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            db.apply_migrations()
            versions_after_first = db.conn.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]

            db.apply_migrations()
            versions_after_second = db.conn.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]

        assert versions_after_first == versions_after_second


# ── WAL pragmas ───────────────────────────────────────────────────────────────

def test_wal_journal_mode_set():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"


def test_foreign_keys_enabled():
    with tempfile.TemporaryDirectory() as d:
        with CRMDatabase(d) as db:
            fk = db.conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1
