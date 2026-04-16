"""Tests for ingestion_health _connect() retry logic and record_run resilience.

Verifies:
- _connect retries on duckdb.IOException with exponential backoff
- _connect succeeds if lock clears before max retries
- _connect raises after exhausting all retries
- _connect does NOT retry on non-IOException errors
- record_run succeeds on a clean DB (happy path sanity check)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import duckdb
import pytest


@pytest.fixture()
def health_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "ingestion_health.duckdb")
    monkeypatch.setenv("INGESTION_HEALTH_DB", db_path)
    return db_path


def test_connect_success_no_retry(health_db):
    """Happy path: _connect opens DB and creates table on first attempt."""
    from orchestration.ops.ingestion_health import _connect

    conn = _connect()
    try:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'ingestion_runs'"
        ).fetchall()
        assert len(tables) == 1
    finally:
        conn.close()


@patch("orchestration.ops.ingestion_health.time.sleep")
def test_connect_retries_on_ioerror_then_succeeds(mock_sleep, health_db):
    """_connect retries on IOException and succeeds when lock clears."""
    from orchestration.ops import ingestion_health as ih

    real_connect = duckdb.connect
    call_count = 0

    def flaky_connect(path, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise duckdb.IOException("Could not set lock on file")
        return real_connect(path, **kwargs)

    with patch.object(duckdb, "connect", side_effect=flaky_connect):
        conn = ih._connect()
        conn.close()

    assert call_count == 2
    mock_sleep.assert_called_once_with(ih._LOCK_BACKOFF_S)


@patch("orchestration.ops.ingestion_health.time.sleep")
def test_connect_raises_after_max_retries(mock_sleep, health_db):
    """_connect raises IOException after exhausting all retries."""
    from orchestration.ops import ingestion_health as ih

    with patch.object(duckdb, "connect", side_effect=duckdb.IOException("lock held")):
        with pytest.raises(duckdb.IOException, match="lock held"):
            ih._connect()

    assert mock_sleep.call_count == ih._LOCK_RETRIES - 1


@patch("orchestration.ops.ingestion_health.time.sleep")
def test_connect_backoff_is_exponential(mock_sleep, health_db):
    """Backoff doubles each retry: 1s, 2s."""
    from orchestration.ops import ingestion_health as ih

    with patch.object(duckdb, "connect", side_effect=duckdb.IOException("lock")):
        with pytest.raises(duckdb.IOException):
            ih._connect()

    waits = [call.args[0] for call in mock_sleep.call_args_list]
    expected = [ih._LOCK_BACKOFF_S * (2 ** i) for i in range(ih._LOCK_RETRIES - 1)]
    assert waits == expected


def test_connect_no_retry_on_other_errors(health_db):
    """Non-IOException errors propagate immediately without retry."""
    from orchestration.ops import ingestion_health as ih

    with patch.object(duckdb, "connect", side_effect=RuntimeError("bad config")):
        with pytest.raises(RuntimeError, match="bad config"):
            ih._connect()


def test_record_run_happy_path(health_db):
    """record_run writes a row that can be read back."""
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
