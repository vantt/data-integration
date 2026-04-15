"""Smoke tests for asset check factories.

Creates a temp DuckDB, seeds rows, and verifies check factories execute
without errors and return the correct pass/warn/fail signals.

Run with: pytest orchestration/asset_checks/__tests__/test_check_factories_smoke.py -v
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import duckdb
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       VARCHAR NOT NULL,
    run_id          VARCHAR NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    duration_s      DOUBLE,
    status          VARCHAR NOT NULL,
    rows_fetched    BIGINT,
    rows_written    BIGINT,
    rows_new        BIGINT,
    rows_updated    BIGINT,
    cursor_before   VARCHAR,
    cursor_after    VARCHAR,
    schema_hash     VARCHAR,
    file_sha256     VARCHAR,
    file_mtime      TIMESTAMPTZ,
    metadata_json   JSON,
    PRIMARY KEY (asset_key, run_id)
);
"""


@pytest.fixture()
def temp_db(tmp_path):
    """Return path to a seeded temp DuckDB."""
    db_path = str(tmp_path / "ingestion_health.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(_DDL)

    now = datetime.now(timezone.utc)
    rows = [
        # healthy asset — recent, has rows
        ("sapo/sapo_orders_batch_asset", "run-001", now - timedelta(hours=2), "success", 1000, 1000),
        ("sapo/sapo_orders_batch_asset", "run-002", now - timedelta(days=1), "success", 900, 900),
        ("sapo/sapo_orders_batch_asset", "run-003", now - timedelta(days=2), "success", 950, 950),
        ("sapo/sapo_orders_batch_asset", "run-004", now - timedelta(days=3), "success", 800, 800),
        ("sapo/sapo_orders_batch_asset", "run-005", now - timedelta(days=4), "success", 1100, 1100),
        ("sapo/sapo_orders_batch_asset", "run-006", now - timedelta(days=5), "success", 750, 750),
        ("sapo/sapo_orders_batch_asset", "run-007", now - timedelta(days=6), "success", 850, 850),
        ("sapo/sapo_orders_batch_asset", "run-008", now - timedelta(days=7), "success", 920, 920),
        # stale asset — last success 50h ago (exceeds 28h SLA)
        ("sapo/sapo_customers_batch_asset", "run-c01", now - timedelta(hours=50), "success", 500, 500),
        # zero-row asset — ran recently but wrote nothing
        ("sapo/sapo_products_batch_asset", "run-p01", now - timedelta(hours=1), "success", 0, 0),
        # cursor-stall asset — cursor moved but no rows for 3 runs
        ("sapo/sapo_history_log_asset", "run-h01", now - timedelta(hours=1), "success", 0, 0, "cursor-A", "cursor-B"),
        ("sapo/sapo_history_log_asset", "run-h02", now - timedelta(hours=2), "success", 0, 0, "cursor-B", "cursor-C"),
        ("sapo/sapo_history_log_asset", "run-h03", now - timedelta(hours=3), "success", 0, 0, "cursor-C", "cursor-D"),
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
            [ak, rid, ts, status, fetched, written, cursor_b, cursor_a],
        )

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
            result = last_success(conn, "sapo/sapo_orders_batch_asset")

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
            rows = rows_by_day(conn, "sapo/sapo_orders_batch_asset", n_days=8)

    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all(isinstance(r, int) for _, r in rows)


def test_consecutive_empty_with_cursor_move_detects_streak(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, consecutive_empty_with_cursor_move

    with _patch_db(temp_db):
        with open_readonly() as conn:
            streak = consecutive_empty_with_cursor_move(conn, "sapo/sapo_history_log_asset", streak_n=3)

    assert streak == 3


def test_consecutive_empty_returns_zero_for_no_cursor_data(temp_db):
    from orchestration.asset_checks.health_db import open_readonly, consecutive_empty_with_cursor_move

    with _patch_db(temp_db):
        with open_readonly() as conn:
            streak = consecutive_empty_with_cursor_move(conn, "sapo/sapo_orders_batch_asset", streak_n=3)

    assert streak == 0  # orders asset has no cursor columns set


# ---------------------------------------------------------------------------
# Tests: freshness check factory
# ---------------------------------------------------------------------------

def test_freshness_check_passes_for_recent_run(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    check_fn = make_freshness_check(sapo_assets.sapo_orders_batch_asset, "sapo/sapo_orders_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is True


def test_freshness_check_fails_for_stale_run(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    # customers_batch last ran 50h ago, SLA=28h
    check_fn = make_freshness_check(sapo_assets.sapo_customers_batch_asset, "sapo/sapo_customers_batch_asset")

    with _patch_db(temp_db):
        result = check_fn(build_asset_context())

    assert result.passed is False
    from dagster import AssetCheckSeverity
    assert result.severity == AssetCheckSeverity.ERROR


def test_freshness_check_warns_for_no_history(temp_db):
    from dagster import build_asset_context
    from orchestration.assets import sapo_assets
    from orchestration.asset_checks.freshness_checks import make_freshness_check

    check_fn = make_freshness_check(sapo_assets.sapo_accounts_batch_asset, "sapo/sapo_accounts_batch_asset")

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

    check_fn = make_not_empty_check(sapo_assets.sapo_products_batch_asset, "sapo/sapo_products_batch_asset")

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

    check_fn = make_cursor_stall_check(sapo_assets.sapo_history_log_asset, "sapo/sapo_history_log_asset")
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
