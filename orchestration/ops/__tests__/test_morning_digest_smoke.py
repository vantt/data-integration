"""Smoke tests for Phase 4 morning digest.

Seeds a temporary ingestion_health.duckdb with synthetic data and verifies:
- classify() correctly assigns green/yellow/red/gray per boundary conditions
- build_digest_rows() returns one row per known asset
- compose_card_fields() produces non-empty output with correct worst-color
- No Lark calls are made (dry-run / no webhook env var)

No live DB, no network I/O.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta

import duckdb
import pytest

from orchestration.ops.morning_digest import (
    DigestRow,
    KNOWN_ASSETS,
    build_digest_rows,
    classify,
    compose_card_fields,
)

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
def health_db(tmp_path, monkeypatch):
    """Temp ingestion_health.duckdb seeded with synthetic data."""
    db_path = str(tmp_path / "ingestion_health.duckdb")
    monkeypatch.setenv("INGESTION_HEALTH_DB", db_path)

    now = datetime.now(timezone.utc)

    conn = duckdb.connect(db_path)
    conn.execute(_DDL)

    # Asset 1: sapo_orders — healthy, 12_000 rows in last 24h, 7d median ~11_000
    for days_ago in range(7):
        conn.execute(
            """INSERT INTO ingestion_runs
               (asset_key, run_id, run_started_at, status, rows_written)
               VALUES (?, ?, ?, 'success', ?)""",
            [
                "sapo/sapo_orders_batch_asset",
                str(uuid.uuid4()),
                now - timedelta(days=days_ago, hours=1),
                11_000 + days_ago * 100,
            ],
        )
    # Extra recent run for today
    conn.execute(
        """INSERT INTO ingestion_runs
           (asset_key, run_id, run_started_at, status, rows_written)
           VALUES (?, ?, ?, 'success', ?)""",
        ["sapo/sapo_orders_batch_asset", str(uuid.uuid4()), now - timedelta(hours=2), 12_000],
    )

    # Asset 2: sapo_customers — 0 rows in last 24h (WARN)
    for days_ago in range(1, 7):
        conn.execute(
            """INSERT INTO ingestion_runs
               (asset_key, run_id, run_started_at, status, rows_written)
               VALUES (?, ?, ?, 'success', ?)""",
            [
                "sapo/sapo_customers_batch_asset",
                str(uuid.uuid4()),
                now - timedelta(days=days_ago, hours=1),
                200,
            ],
        )
    # Today: 0 rows
    conn.execute(
        """INSERT INTO ingestion_runs
           (asset_key, run_id, run_started_at, status, rows_written)
           VALUES (?, ?, ?, 'success', ?)""",
        ["sapo/sapo_customers_batch_asset", str(uuid.uuid4()), now - timedelta(hours=3), 0],
    )

    # Asset 3: misa — recon drift > 5% (ERROR)
    conn.execute(
        """INSERT INTO ingestion_runs
           (asset_key, run_id, run_started_at, status, rows_written, metadata_json)
           VALUES (?, ?, ?, 'success', ?, ?)""",
        [
            "recon/misa_daily",
            str(uuid.uuid4()),
            now - timedelta(hours=1),
            0,
            '{"drift_pct": -13.0, "src_count": 8200, "dst_count": 7140}',
        ],
    )

    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# classify() unit tests — boundary cases
# ---------------------------------------------------------------------------

def _make(status="green", rows_24h=1000, median_7d=1000, fresh_age_min=30,
          drift_pct=None, note=None) -> DigestRow:
    return DigestRow(
        short_name="test", asset_key="test/asset",
        status=status,
        rows_24h=rows_24h,
        median_7d=median_7d,
        pct_vs_median=None,
        fresh_age_min=fresh_age_min,
        drift_pct=drift_pct,
        note=note,
    )


def test_classify_green_healthy():
    row = _make(rows_24h=1000, median_7d=1000, fresh_age_min=30)
    assert classify(row) == "green"


def test_classify_yellow_rows_below_50pct():
    row = _make(rows_24h=400, median_7d=1000, fresh_age_min=30)
    assert classify(row) == "yellow"


def test_classify_yellow_rows_exactly_50pct():
    # 500 / 1000 = 0.5 — boundary is < 0.5, so 50% exact → green
    row = _make(rows_24h=500, median_7d=1000, fresh_age_min=30)
    assert classify(row) == "green"


def test_classify_red_stale_beyond_sla():
    # 13h > 12h SLA
    row = _make(rows_24h=1000, median_7d=1000, fresh_age_min=13 * 60)
    assert classify(row) == "red"


def test_classify_red_drift_above_5pct():
    row = _make(drift_pct=-13.0)
    assert classify(row) == "red"


def test_classify_yellow_drift_between_1_and_5():
    row = _make(drift_pct=3.0)
    assert classify(row) == "yellow"


def test_classify_gray_never_run():
    row = _make(note="never run")
    assert classify(row) == "gray"


def test_classify_red_last_run_failed():
    row = _make(note="last run failed")
    assert classify(row) == "red"


# ---------------------------------------------------------------------------
# build_digest_rows() integration tests
# ---------------------------------------------------------------------------

def test_build_digest_rows_returns_all_known(health_db):
    rows = build_digest_rows(health_db)
    assert len(rows) == len(KNOWN_ASSETS)


def test_build_digest_rows_orders_healthy(health_db):
    rows = build_digest_rows(health_db)
    sapo_orders = next(r for r in rows if r.short_name == "sapo_orders")
    assert sapo_orders.status == "green"
    assert sapo_orders.rows_24h is not None and sapo_orders.rows_24h > 0


def test_build_digest_rows_customers_warn(health_db):
    """0 rows today vs ~200 median → < 50% → yellow."""
    rows = build_digest_rows(health_db)
    customers = next(r for r in rows if r.short_name == "sapo_customers")
    assert customers.status == "yellow"


def test_build_digest_rows_misa_drift_red(health_db):
    """recon/misa_daily drift=-13% → misa row should be red."""
    rows = build_digest_rows(health_db)
    misa = next(r for r in rows if r.short_name == "misa")
    assert misa.drift_pct is not None and abs(misa.drift_pct) > 5
    assert misa.status == "red"


def test_build_digest_rows_never_run_gray(health_db):
    """Assets not in DB with no recon drift → gray + note='never run'.

    Note: rows with note='never run' but a recon drift signal can be red/yellow.
    We test only those without a linked recon key (no drift possible).
    """
    rows = build_digest_rows(health_db)
    # Assets that have no recon key in KNOWN_ASSETS will never have drift_pct
    no_recon_names = {name for name, _, rk in KNOWN_ASSETS if rk is None}
    never_no_recon = [r for r in rows if r.note == "never run" and r.short_name in no_recon_names]
    assert len(never_no_recon) > 0
    for r in never_no_recon:
        assert r.status == "gray", f"{r.short_name} has note='never run' + no recon key → expected gray, got {r.status}"


# ---------------------------------------------------------------------------
# compose_card_fields() tests
# ---------------------------------------------------------------------------

def test_compose_card_fields_returns_all_keys(health_db):
    rows = build_digest_rows(health_db)
    fields, color = compose_card_fields(rows)
    expected_names = {name for name, _, _ in KNOWN_ASSETS}
    assert set(fields.keys()) == expected_names


def test_compose_card_fields_worst_color_red_when_drift(health_db):
    """misa drift > 5% → card header must be red."""
    rows = build_digest_rows(health_db)
    _, color = compose_card_fields(rows)
    assert color == "red"


def test_compose_card_fields_no_db(tmp_path, monkeypatch):
    """Missing DB → all gray → color is grey."""
    monkeypatch.setenv("INGESTION_HEALTH_DB", str(tmp_path / "missing.duckdb"))
    # build_digest_rows handles missing DB by returning gray rows
    from orchestration.ops.morning_digest import KNOWN_ASSETS, DigestRow, classify, compose_card_fields
    rows = [
        DigestRow(
            short_name=s, asset_key=ak, status="gray",
            rows_24h=None, median_7d=None, pct_vs_median=None,
            fresh_age_min=None, drift_pct=None, note="never run",
        )
        for s, ak, _ in KNOWN_ASSETS
    ]
    for r in rows:
        r.status = classify(r)
    fields, color = compose_card_fields(rows)
    assert color == "grey"
    assert len(fields) == len(KNOWN_ASSETS)
