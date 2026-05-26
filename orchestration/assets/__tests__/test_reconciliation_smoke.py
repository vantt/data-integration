"""Smoke tests for Phase 3 reconciliation logic.

Seeds a temporary ingestion_health.db (SQLite) with synthetic data and verifies:
- drift calculation is correct
- _file_drop_source_count returns correct sum from health DB
- recon assets can be imported without live API calls
- asset checks can be imported

No live API calls — RECON_LIVE_API is never set in this test suite.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone, timedelta

import sqlite3

import duckdb
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def health_db(tmp_path, monkeypatch):
    """Temp ingestion_health.db (SQLite) seeded with synthetic recon + ingestion data."""
    db_path = str(tmp_path / "ingestion_health.db")
    monkeypatch.setenv("INGESTION_HEALTH_DB", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE ingestion_runs (
            asset_key       TEXT NOT NULL,
            run_id          TEXT NOT NULL,
            run_started_at  TEXT NOT NULL,
            run_ended_at    TEXT,
            duration_s      REAL,
            status          TEXT NOT NULL,
            rows_fetched    INTEGER,
            rows_written    INTEGER,
            rows_new        INTEGER,
            rows_updated    INTEGER,
            cursor_before   TEXT,
            cursor_after    TEXT,
            schema_hash     TEXT,
            file_sha256     TEXT,
            file_mtime      TEXT,
            metadata_json   TEXT,
            PRIMARY KEY (asset_key, run_id)
        )
    """)

    now = datetime.now(timezone.utc)
    five_days_ago = now - timedelta(days=5)
    three_days_ago = now - timedelta(days=3)

    # Shopee ingestion runs: total rows_written = 500
    conn.execute(
        "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["shopee/shopee_income_file_drop_asset", str(uuid.uuid4()),
         five_days_ago.isoformat(), five_days_ago.isoformat(), 10.0,
         "success", 300, 300, 300, 0, None, None, None, None, None, None],
    )
    conn.execute(
        "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["shopee/shopee_income_file_drop_asset", str(uuid.uuid4()),
         three_days_ago.isoformat(), three_days_ago.isoformat(), 10.0,
         "success", 200, 200, 200, 0, None, None, None, None, None, None],
    )

    # MISA ingestion run: rows_written = 150
    conn.execute(
        "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["misa_amis/misa_sales_file_drop_asset", str(uuid.uuid4()),
         three_days_ago.isoformat(), three_days_ago.isoformat(), 8.0,
         "success", 150, 150, 150, 0, None, None, None, None, None, None],
    )

    # Existing recon row for shopee with drift_pct=0.02 (> 1% → WARN)
    import json
    meta = json.dumps({"source_count": 500, "dest_count": 510, "drift_pct": 0.02,
                       "window_start": five_days_ago.isoformat(),
                       "window_end": now.isoformat()})
    conn.execute(
        "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ["recon/shopee_daily", str(uuid.uuid4()),
         now.isoformat(), now.isoformat(), 1.0,
         "success", 500, 510, None, None, None, None, None, None, None, meta],
    )

    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Unit: _compute_drift
# ---------------------------------------------------------------------------

def test_compute_drift_exact():
    from orchestration.assets.reconciliation import _compute_drift

    assert _compute_drift(1000, 1010) == pytest.approx(0.01)


def test_compute_drift_negative():
    from orchestration.assets.reconciliation import _compute_drift

    assert _compute_drift(1000, 990) == pytest.approx(-0.01)


def test_compute_drift_none_source():
    from orchestration.assets.reconciliation import _compute_drift

    assert _compute_drift(None, 100) is None


def test_compute_drift_zero_source():
    from orchestration.assets.reconciliation import _compute_drift

    assert _compute_drift(0, 100) is None


# ---------------------------------------------------------------------------
# Unit: _file_drop_source_count reads health DB correctly
# ---------------------------------------------------------------------------

def test_file_drop_source_count_shopee(health_db, monkeypatch):
    monkeypatch.setenv("INGESTION_HEALTH_DB", health_db)

    # Re-import to pick up patched env
    import importlib
    import orchestration.ops.ingestion_health as ih
    importlib.reload(ih)

    from orchestration.assets.reconciliation import _file_drop_source_count
    from datetime import datetime, timezone, timedelta

    window_start = datetime.now(timezone.utc) - timedelta(days=7)
    total = _file_drop_source_count("shopee/shopee_income_file_drop_asset", window_start)
    assert total == 500  # 300 + 200


def test_file_drop_source_count_misa(health_db, monkeypatch):
    monkeypatch.setenv("INGESTION_HEALTH_DB", health_db)

    import importlib
    import orchestration.ops.ingestion_health as ih
    importlib.reload(ih)

    from orchestration.assets.reconciliation import _file_drop_source_count
    from datetime import datetime, timezone, timedelta

    window_start = datetime.now(timezone.utc) - timedelta(days=7)
    total = _file_drop_source_count("misa_amis/misa_sales_file_drop_asset", window_start)
    assert total == 150


def test_file_drop_source_count_no_runs(health_db, monkeypatch):
    monkeypatch.setenv("INGESTION_HEALTH_DB", health_db)

    import importlib
    import orchestration.ops.ingestion_health as ih
    importlib.reload(ih)

    from orchestration.assets.reconciliation import _file_drop_source_count
    from datetime import datetime, timezone, timedelta

    window_start = datetime.now(timezone.utc) - timedelta(days=7)
    total = _file_drop_source_count("nonexistent/asset", window_start)
    assert total is None


# ---------------------------------------------------------------------------
# Smoke: import reconciliation module without live API
# ---------------------------------------------------------------------------

def test_import_reconciliation_no_live_api(monkeypatch):
    monkeypatch.delenv("RECON_LIVE_API", raising=False)
    # Should not raise; live API guarded behind env flag
    import orchestration.assets.reconciliation  # noqa: F401


def test_import_api_count_no_live_api(monkeypatch):
    monkeypatch.delenv("RECON_LIVE_API", raising=False)
    # count_orders/count_customers must return None without hitting Sapo
    import sys
    # Ensure sapo package path available
    sapo_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "ingestion", "src"
    )
    if sapo_path not in sys.path:
        sys.path.insert(0, sapo_path)

    from sapo.api_count import count_orders, count_customers
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    assert count_orders(now - timedelta(days=1), now) is None
    assert count_customers(now - timedelta(days=1), now) is None


# ---------------------------------------------------------------------------
# Smoke: import reconciliation_checks
# ---------------------------------------------------------------------------

def test_import_reconciliation_checks():
    from orchestration.asset_checks.reconciliation_checks import RECON_CHECKS
    assert len(RECON_CHECKS) == 4
    # Verify each check has correct spec name
    specs = [spec for c in RECON_CHECKS for spec in c.check_specs]
    assert all(s.name == "drift_within_threshold" for s in specs)


# ---------------------------------------------------------------------------
# Unit: drift check factory logic (threshold constants)
# ---------------------------------------------------------------------------

def test_warn_threshold_constant():
    """Verify WARN threshold is 1% as documented."""
    from orchestration.asset_checks.reconciliation_checks import _WARN_THRESHOLD, _ERROR_THRESHOLD
    assert _WARN_THRESHOLD == 0.01
    assert _ERROR_THRESHOLD == 0.05


def test_drift_above_warn_below_error():
    """drift_pct=0.02 is between thresholds — should be WARN territory."""
    from orchestration.asset_checks.reconciliation_checks import _WARN_THRESHOLD, _ERROR_THRESHOLD
    drift = 0.02
    assert abs(drift) > _WARN_THRESHOLD
    assert abs(drift) <= _ERROR_THRESHOLD


def test_drift_above_error_threshold():
    """drift_pct=0.10 exceeds ERROR threshold."""
    from orchestration.asset_checks.reconciliation_checks import _ERROR_THRESHOLD
    drift = 0.10
    assert abs(drift) > _ERROR_THRESHOLD


# ---------------------------------------------------------------------------
# Unit: _persist_recon exception handling
# ---------------------------------------------------------------------------

def test_persist_recon_swallows_db_error(health_db, monkeypatch):
    """_persist_recon must not raise when record_run fails (best-effort write)."""
    from unittest.mock import patch
    from orchestration.assets.reconciliation import _persist_recon

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)

    with patch(
        "orchestration.assets.reconciliation.record_run",
        side_effect=duckdb.IOException("Could not set lock on file"),
    ):
        _persist_recon(
            asset_key="recon/test",
            run_id=str(uuid.uuid4()),
            started=now,
            source_count=100,
            dest_count=100,
            drift_pct=0.0,
            window_start=yesterday,
            window_end=now,
        )


def test_persist_recon_writes_when_db_available(health_db, monkeypatch):
    """_persist_recon writes successfully when DB is accessible."""
    import importlib
    import orchestration.ops.ingestion_health as ih
    importlib.reload(ih)

    from orchestration.assets.reconciliation import _persist_recon

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    run_id = str(uuid.uuid4())

    _persist_recon(
        asset_key="recon/test_write",
        run_id=run_id,
        started=now,
        source_count=200,
        dest_count=195,
        drift_pct=-0.025,
        window_start=yesterday,
        window_end=now,
    )

    conn = sqlite3.connect(health_db)
    row = conn.execute(
        "SELECT asset_key, rows_fetched, rows_written FROM ingestion_runs WHERE run_id = ?",
        [run_id],
    ).fetchone()
    conn.close()
    assert row == ("recon/test_write", 200, 195)
