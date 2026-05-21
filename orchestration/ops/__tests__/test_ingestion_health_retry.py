"""Tests for ingestion_health SQLite backend.

Verifies:
- _connect() creates table and enables WAL mode
- record_run() writes a row and is idempotent (INSERT OR REPLACE)
- Concurrent writes succeed without lock errors (SQLite WAL)
- check_writable() returns True on a valid path
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest


@pytest.fixture()
def health_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "ingestion_health.db")
    monkeypatch.setenv("INGESTION_HEALTH_DB", db_path)
    return db_path


def test_connect_creates_table_and_wal(health_db):
    """_connect() creates ingestion_runs table and enables WAL mode."""
    from orchestration.ops.ingestion_health import _connect

    conn = _connect()
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ingestion_runs'"
        ).fetchall()
        assert len(tables) == 1
    finally:
        conn.close()


def test_record_run_happy_path(health_db):
    """record_run() writes a row that can be read back."""
    from orchestration.ops.ingestion_health import record_run, _connect

    now = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())

    record_run(
        asset_key="test/asset",
        run_id=run_id,
        run_started_at=now,
        status="success",
        rows_written=42,
    )

    conn = _connect()
    try:
        row = conn.execute(
            "SELECT asset_key, rows_written FROM ingestion_runs WHERE run_id = ?",
            [run_id],
        ).fetchone()
        assert row == ("test/asset", 42)
    finally:
        conn.close()


def test_record_run_idempotent(health_db):
    """INSERT OR REPLACE: second call with same (asset_key, run_id) updates the row."""
    from orchestration.ops.ingestion_health import record_run, _connect

    now = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())

    record_run(asset_key="test/asset", run_id=run_id, run_started_at=now, rows_written=10)
    record_run(asset_key="test/asset", run_id=run_id, run_started_at=now, rows_written=99)

    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT rows_written FROM ingestion_runs WHERE run_id = ?", [run_id]
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 99
    finally:
        conn.close()


def test_concurrent_writes_no_lock_error(health_db):
    """Multiple threads can write simultaneously under WAL mode."""
    import threading
    from orchestration.ops.ingestion_health import record_run

    now = datetime.now(timezone.utc)
    errors: list[Exception] = []

    def write(i: int) -> None:
        try:
            record_run(
                asset_key=f"asset/{i}",
                run_id=str(uuid.uuid4()),
                run_started_at=now,
                status="success",
                rows_written=i,
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Concurrent write errors: {errors}"


def test_check_writable_returns_true(health_db):
    """check_writable() returns (True, '') on a valid SQLite path."""
    from orchestration.ops.ingestion_health import check_writable

    ok, err = check_writable()
    assert ok is True
    assert err == ""
