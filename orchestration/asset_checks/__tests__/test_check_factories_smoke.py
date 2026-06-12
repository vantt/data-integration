"""Smoke tests for asset check factories.

Creates a temp SQLite DB, seeds rows, and verifies check factories execute
without errors and return the correct pass/warn/fail signals.

Run with: pytest orchestration/asset_checks/__tests__/test_check_factories_smoke.py -v
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       TEXT NOT NULL,
    run_id          TEXT NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
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
    file_mtime      TIMESTAMPTZ,
    metadata_json   TEXT,
    PRIMARY KEY (asset_key, run_id)
);
"""


@pytest.fixture()
def temp_db(tmp_path):
    """Return path to a seeded temp SQLite DB."""
    db_path = str(tmp_path / "ingestion_health.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_DDL)

    now = datetime.now(timezone.utc)
    rows = [
        # healthy asset — recent, has rows
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-001", now - timedelta(hours=2), "success", 1000, 1000),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-002", now - timedelta(days=1), "success", 900, 900),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-003", now - timedelta(days=2), "success", 950, 950),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-004", now - timedelta(days=3), "success", 800, 800),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-005", now - timedelta(days=4), "success", 1100, 1100),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-006", now - timedelta(days=5), "success", 750, 750),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-007", now - timedelta(days=6), "success", 850, 850),
        ("sapo/ingest_sapo_v2_orders_batch_asset", "run-008", now - timedelta(days=7), "success", 920, 920),
        # stale asset — last success 50h ago (exceeds 28h SLA)
        ("sapo/ingest_sapo_v2_customers_batch_asset", "run-c01", now - timedelta(hours=50), "success", 500, 500),
        # zero-row asset — ran recently but wrote nothing
        ("sapo/ingest_sapo_v2_products_batch_asset", "run-p01", now - timedelta(hours=1), "success", 0, 0),
        # cursor-stall asset — cursor moved but no rows for 3 runs
        ("sapo/ingest_sapo_v2_history_log_asset", "run-h01", now - timedelta(hours=1), "success", 0, 0, "cursor-A", "cursor-B"),
        ("sapo/ingest_sapo_v2_history_log_asset", "run-h02", now - timedelta(hours=2), "success", 0, 0, "cursor-B", "cursor-C"),
        ("sapo/ingest_sapo_v2_history_log_asset", "run-h03", now - timedelta(hours=3), "success", 0, 0, "cursor-C", "cursor-D"),
    ]

    for row in rows:
        if len(row) == 6:
            ak, rid, ts, status, fetched, written = row
            cursor_b = cursor_a = None
        else:
            ak, rid, ts, status, fetched, written, cursor_b, cursor_a = row

        conn.execute(
            "INSERT OR REPLACE INTO ingestion_runs "
            "(asset_key, run_id, run_started_at, status, rows_fetched, rows_written, cursor_before, cursor_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [ak, rid, ts.isoformat(), status, fetched, written, cursor_b, cursor_a],
        )

    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Helpers: patch get_db_path to point at temp DB
# ---------------------------------------------------------------------------

def _patch_db(db_path):
    return patch("orchestration.asset_checks.health_db.get_db_path", return_value=db_path)


# ---------------------------------------------------------------------------
# Tests: health_db helpers
# ---------------------------------------------------------------------------

def test_last_success_returns_datetime(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, last_success

    with _patch_db(temp_db):
        with open_readonly() as conn:
            result = last_success(conn, "sapo/ingest_sapo_v2_orders_batch_asset")

    assert result is not None
    assert isinstance(result, datetime)


def test_last_success_returns_none_for_unknown_key(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, last_success

    with _patch_db(temp_db):
        with open_readonly() as conn:
            result = last_success(conn, "unknown/unknown_asset")

    assert result is None


def test_rows_by_day_returns_list(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, rows_by_day

    with _patch_db(temp_db):
        with open_readonly() as conn:
            rows = rows_by_day(conn, "sapo/ingest_sapo_v2_orders_batch_asset", n_days=8)

    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all(isinstance(r, int) for _, r in rows)


def test_consecutive_empty_with_cursor_move_detects_streak(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, consecutive_empty_with_cursor_move

    with _patch_db(temp_db):
        with open_readonly() as conn:
            streak = consecutive_empty_with_cursor_move(conn, "sapo/ingest_sapo_v2_history_log_asset", streak_n=3)

    assert streak == 3


def test_consecutive_empty_returns_zero_for_no_cursor_data(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, consecutive_empty_with_cursor_move

    with _patch_db(temp_db):
        with open_readonly() as conn:
            streak = consecutive_empty_with_cursor_move(conn, "sapo/ingest_sapo_v2_orders_batch_asset", streak_n=3)

    assert streak == 0  # orders asset has no cursor columns set


# ---------------------------------------------------------------------------
# Tests: freshness check factory
# ---------------------------------------------------------------------------

def test_freshness_check_passes_for_recent_run(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    check_fn = make_freshness_check(sapo_assets.ingest_sapo_v2_orders_batch_asset, "sapo/ingest_sapo_v2_orders_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is True


def test_freshness_check_fails_for_stale_run(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    # customers_batch last ran 50h ago, SLA=28h
    check_fn = make_freshness_check(sapo_assets.ingest_sapo_v2_customers_batch_asset, "sapo/ingest_sapo_v2_customers_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is False
    from dagster import AssetCheckSeverity
    assert result.severity == AssetCheckSeverity.ERROR


def test_freshness_check_warns_for_no_history(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    check_fn = make_freshness_check(sapo_assets.ingest_sapo_v2_accounts_batch_asset, "sapo/ingest_sapo_v2_accounts_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    # No rows for accounts — should return passed=True with WARN description
    assert result.passed is True
    assert "No successful runs" in result.description


# ---------------------------------------------------------------------------
# Tests: not_empty check
# ---------------------------------------------------------------------------

def test_not_empty_check_warns_for_zero_rows(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.row_trend_checks import make_not_empty_check

    check_fn = make_not_empty_check(sapo_assets.ingest_sapo_v2_products_batch_asset, "sapo/ingest_sapo_v2_products_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is False


# ---------------------------------------------------------------------------
# Tests: cursor stall check
# ---------------------------------------------------------------------------

def test_cursor_stall_check_detects_streak(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.cursor_checks import make_cursor_stall_check

    check_fn = make_cursor_stall_check(sapo_assets.ingest_sapo_v2_history_log_asset, "sapo/ingest_sapo_v2_history_log_asset")
    assert check_fn is not None

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is False


def test_cursor_stall_check_returns_none_for_non_sapo(temp_db):
    from orchestration.assets import shopee_assets
    from orchestration.asset_checks.cursor_checks import make_cursor_stall_check

    result = make_cursor_stall_check(shopee_assets.shopee_income_file_drop_asset, "shopee/shopee_income_file_drop_asset")
    assert result is None


# ---------------------------------------------------------------------------
# Tests: ALL_CHECKS registry
# ---------------------------------------------------------------------------

def test_all_checks_is_non_empty():
    from orchestration.asset_checks import ALL_CHECKS
    assert len(ALL_CHECKS) > 0


def test_all_checks_count_reasonable():
    """10 assets × 2–4 checks each = at least 20 checks registered."""
    from orchestration.asset_checks import ALL_CHECKS
    assert len(ALL_CHECKS) >= 20
