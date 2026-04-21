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
          drift_pct=None, note=None, zero_streak=0) -> DigestRow:
    return DigestRow(
        short_name="test", asset_key="test/asset",
        status=status,
        rows_24h=rows_24h,
        median_7d=median_7d,
        pct_vs_median=None,
        fresh_age_min=fresh_age_min,
        drift_pct=drift_pct,
        note=note,
        zero_streak=zero_streak,
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
    rows, _ = build_digest_rows(health_db)
    assert len(rows) == len(KNOWN_ASSETS)


def test_build_digest_rows_orders_healthy(health_db):
    rows, _ = build_digest_rows(health_db)
    sapo_orders = next(r for r in rows if r.short_name == "sapo_orders")
    assert sapo_orders.status == "green"
    assert sapo_orders.rows_24h is not None and sapo_orders.rows_24h > 0


def test_build_digest_rows_customers_warn(health_db):
    """0 rows today vs ~200 median → < 50% → yellow."""
    rows, _ = build_digest_rows(health_db)
    customers = next(r for r in rows if r.short_name == "sapo_customers")
    assert customers.status == "yellow"


def test_build_digest_rows_misa_drift_red(health_db):
    """recon/misa_daily drift=-13% → misa row should be red."""
    rows, _ = build_digest_rows(health_db)
    misa = next(r for r in rows if r.short_name == "misa")
    assert misa.drift_pct is not None and abs(misa.drift_pct) > 5
    assert misa.status == "red"


def test_build_digest_rows_never_run_gray(health_db):
    """Assets not in DB with no recon drift → gray + note='never run'.

    Note: rows with note='never run' but a recon drift signal can be red/yellow.
    We test only those without a linked recon key (no drift possible).
    """
    rows, _ = build_digest_rows(health_db)
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
    """Card now uses Vietnamese display labels + a summary header line."""
    from orchestration.ops.morning_digest import ASSET_DISPLAY
    rows, _ = build_digest_rows(health_db)
    fields, color = compose_card_fields(rows)
    expected_labels = {ASSET_DISPLAY[name][0] for name, _, _ in KNOWN_ASSETS}
    # Summary header is always present
    assert "📊 Tổng quan" in fields
    # All known assets render under their Vietnamese label
    assert expected_labels.issubset(set(fields.keys()))


def test_compose_card_fields_worst_color_red_when_drift(health_db):
    """misa drift > 5% → card header must be red."""
    rows, _ = build_digest_rows(health_db)
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
    # KNOWN_ASSETS rows + 1 summary header
    assert len(fields) == len(KNOWN_ASSETS) + 1
    assert "📊 Tổng quan" in fields


# ---------------------------------------------------------------------------
# New feature tests: zero-streak, run links, recommendations
# ---------------------------------------------------------------------------

def test_classify_red_zero_streak_3():
    row = _make(zero_streak=3)
    assert classify(row) == "red"


def test_classify_yellow_zero_streak_2():
    row = _make(zero_streak=2)
    assert classify(row) == "yellow"


def test_classify_green_zero_streak_1():
    row = _make(zero_streak=1)
    assert classify(row) == "green"


def _label_for(short_name: str) -> str:
    """Resolve Vietnamese display label for a short_name (fallback = short_name)."""
    from orchestration.ops.morning_digest import ASSET_DISPLAY
    return ASSET_DISPLAY.get(short_name, (short_name, "batch", "dòng"))[0]


def _make_known(**kwargs) -> DigestRow:
    """DigestRow that uses a real KNOWN_ASSETS short_name so ASSET_DISPLAY resolves."""
    base = dict(short_name="sapo_orders", asset_key="sapo/sapo_orders_batch_asset",
                status="green", rows_24h=1000, median_7d=1000, pct_vs_median=None,
                fresh_age_min=30, drift_pct=None, note=None, zero_streak=0)
    base.update(kwargs)
    return DigestRow(**base)


def test_compose_card_no_run_link_for_green():
    """Green rows should NOT have run links (keep card clean)."""
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_known()
    row.last_run_id = "abcdef12-3456-7890-abcd-ef1234567890"
    fields, _ = compose_card_fields([row])
    assert "abcdef12" not in fields[_label_for("sapo_orders")]


def test_compose_card_includes_zero_streak_warning():
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_known(zero_streak=3)
    row.status = classify(row)
    fields, _ = compose_card_fields([row])
    assert "3 lần liên tiếp 0 dòng" in fields[_label_for("sapo_orders")]


def test_compose_card_includes_recommendation_for_failed():
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_known(note="last run failed")
    row.status = classify(row)
    fields, _ = compose_card_fields([row])
    assert "chạy lại asset" in fields[_label_for("sapo_orders")]


def test_compose_card_includes_run_link_for_red():
    """Red rows SHOULD have run links."""
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_known(note="last run failed")
    row.last_run_id = "abcdef12-3456-7890-abcd-ef1234567890"
    row.status = classify(row)
    fields, _ = compose_card_fields([row])
    assert "abcdef12" in fields[_label_for("sapo_orders")]


def test_compose_card_summary_header_present():
    """Card always carries a summary header counting healthy/warn/error assets."""
    from orchestration.ops.morning_digest import compose_card_fields
    healthy = _make_known()
    warn = _make_known(short_name="sapo_customers",
                       asset_key="sapo/sapo_customers_batch_asset",
                       drift_pct=3.0)
    warn.status = classify(warn)
    fields, _ = compose_card_fields([healthy, warn])
    summary = fields["📊 Tổng quan"]
    assert "khoẻ" in summary
    assert "cảnh báo" in summary


def test_build_digest_rows_populates_run_id(health_db):
    rows, _ = build_digest_rows(health_db)
    orders = next(r for r in rows if r.short_name == "sapo_orders")
    assert orders.last_run_id is not None


# ---------------------------------------------------------------------------
# Format-path tests: lock down cursor / batch / file_drop branches in
# _format_row_vi so a future ASSET_DISPLAY edit can't silently regress.
# ---------------------------------------------------------------------------

def _make_with_runs(short_name: str, asset_key: str, **kwargs) -> DigestRow:
    base = dict(short_name=short_name, asset_key=asset_key,
                status="green", rows_24h=0, median_7d=None, pct_vs_median=None,
                fresh_age_min=10, drift_pct=None, note=None, zero_streak=0,
                runs_24h=0, last_status="success")
    base.update(kwargs)
    return DigestRow(**base)


def test_format_cursor_zero_rows_emphasises_run_count():
    """Cursor asset with 0 rows should NOT look like a problem — it's normal."""
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("sapo_webhook", "sapo/sapo_webhook_consumer_asset",
                          rows_24h=0, runs_24h=347, last_status="skipped")
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("sapo_webhook")]
    assert "Không có" in val and "đơn" in val
    assert "347 lần/24h" in val
    assert "✅" in val  # green


def test_format_cursor_with_rows_shows_count():
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("sapo_history", "sapo/sapo_history_log_asset",
                          rows_24h=1234, runs_24h=88, last_status="success")
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("sapo_history")]
    assert "1.234" in val  # Vietnamese thousand separator
    assert "dòng mới" in val
    assert "88 lần/24h" in val


def test_format_batch_zero_rows_says_no_new():
    """Batch with 0 rows should say 'không có ... mới' (not 'Batch hôm nay: 0')."""
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("sapo_orders", "sapo/sapo_orders_batch_asset",
                          rows_24h=0, runs_24h=1, last_status="skipped")
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("sapo_orders")]
    assert "không có đơn mới" in val
    assert "Batch hôm nay" in val


def test_format_file_drop_zero_says_unchanged():
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("sheet_targets", "sheets/sheets_targets_asset",
                          rows_24h=0, runs_24h=1, last_status="skipped")
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("sheet_targets")]
    assert "File nguồn chưa thay đổi" in val


def test_format_file_drop_with_new_data():
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("shopee", "shopee/shopee_income_file_drop_asset",
                          rows_24h=2500, runs_24h=1, last_status="success")
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("shopee")]
    assert "2.500" in val
    assert "File mới" in val


def test_format_small_drift_annotation_under_5_pct():
    """Drift between 0 and 5% should annotate, not override main message."""
    from orchestration.ops.morning_digest import compose_card_fields
    row = _make_with_runs("sapo_orders", "sapo/sapo_orders_batch_asset",
                          rows_24h=0, runs_24h=1, last_status="skipped",
                          drift_pct=-1.0)
    row.status = classify(row)  # drift -1.0 stays green (boundary > 1.0 is yellow)
    fields, _ = compose_card_fields([row])
    val = fields[_label_for("sapo_orders")]
    assert "Batch hôm nay" in val
    assert "lệch source: -1.0%" in val


def test_compose_card_field_order_summary_first():
    """Summary header MUST be the first field — Lark renders dict in insertion order."""
    from orchestration.ops.morning_digest import compose_card_fields, KpiData
    row = _make_with_runs("sapo_orders", "sapo/sapo_orders_batch_asset")
    kpi = KpiData(source_revenue=1000.0, warehouse_revenue=1000.0,
                  drift_pct=0.0, date_key=20260420, status="success")
    fields, _ = compose_card_fields([row], kpi)
    keys = list(fields.keys())
    assert keys[0] == "📊 Tổng quan"
    assert keys[1] == "💰 Doanh thu hôm qua"


def test_compose_card_empty_rows_no_summary():
    """Empty rows: skip summary line and fall back to grey (no-data state).

    Defensive guard — caller (compose_and_send_digest) already early-returns on
    empty rows, but compose_card_fields must not signal 'all healthy' on no data.
    """
    from orchestration.ops.morning_digest import compose_card_fields
    fields, color = compose_card_fields([])
    assert "📊 Tổng quan" not in fields
    assert fields == {}
    assert color == "grey"


def test_compose_card_empty_rows_with_kpi_uses_kpi_color():
    """Empty rows but KPI is red → color reflects KPI severity, not the gray fallback."""
    from orchestration.ops.morning_digest import compose_card_fields, KpiData
    bad_kpi = KpiData(source_revenue=1e9, warehouse_revenue=8e8,
                      drift_pct=-0.20, date_key=20260420, status="success")
    fields, color = compose_card_fields([], bad_kpi)
    assert "📊 Tổng quan" not in fields  # no asset rows → no summary
    assert "💰 Doanh thu hôm qua" in fields
    assert color == "red"  # KPI drift -20% → red, NOT grey


def test_compose_card_empty_rows_with_disabled_kpi_grey():
    """Empty rows + disabled KPI → grey (no signal at all)."""
    from orchestration.ops.morning_digest import compose_card_fields, KpiData
    disabled = KpiData(source_revenue=None, warehouse_revenue=None,
                       drift_pct=None, date_key=None, status="disabled")
    fields, color = compose_card_fields([], disabled)
    assert fields == {}
    assert color == "grey"


def test_format_ages_vietnamese():
    """_fmt_age_vi: 30m → 'phút', 5h → 'giờ', >24h → 'ngày'."""
    from orchestration.ops.morning_digest import _fmt_age_vi
    assert "phút" in _fmt_age_vi(30)
    assert "giờ" in _fmt_age_vi(180)
    assert "ngày" in _fmt_age_vi(48 * 60)
    assert _fmt_age_vi(None) == "chưa rõ"
