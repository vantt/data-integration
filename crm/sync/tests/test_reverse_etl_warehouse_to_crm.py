"""
test_reverse_etl_warehouse_to_crm.py — end-to-end pytest suite for the Python reverse-ETL.

Uses a synthetic DuckDB fixture (main_marts.* tables in a temp dir) instead of the
real warehouse, so all tests pass without olap.duckdb present on this machine.

Coverage:
  T1  rows land in every wh_* table after one run
  T2  idempotent: run twice → counts stable, no duplicates
  T3  wh_party_seed populated from customer_base customer_id/customer_key
  T4  wh_sync_run logged with status='ok' for each source table
  T5  incremental: second run with higher date_key only loads new orders
  T6  missing-column fixture → MissingColumnError raised (dbt-rename guard)
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
import tempfile
from typing import Generator

import pytest

# Ensure repo root is on sys.path so `crm.sync.*` is importable.
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import duckdb  # noqa: E402

from crm.sync import duckdb_reader as dr  # noqa: E402
from crm.sync import sqlite_upsert as su  # noqa: E402
from crm.sync.duckdb_reader import MissingColumnError  # noqa: E402
from crm.sync.reverse_etl_warehouse_to_crm import run  # noqa: E402


# ─── Synthetic DuckDB fixture factory ────────────────────────────────────────

def _make_warehouse(path: str) -> duckdb.DuckDBPyConnection:
    """
    Create an in-file DuckDB at path with main_marts schema tables matching
    the column contracts in duckdb_reader.py.
    """
    conn = duckdb.connect(path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts")

    # dim_customers — covers both insight + base column sets
    # Note: live warehouse uses full_name (not display_name); duckdb_reader aliases it back
    # first_order_date must be DATE (not TEXT) so strftime() in fetch_customer_base resolves
    conn.execute("""
        CREATE TABLE main_marts.dim_customers (
            customer_key TEXT,
            customer_id BIGINT,
            customer_code TEXT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            customer_group TEXT,
            first_order_date DATE,
            value_group TEXT,
            customer_status TEXT,
            next_purchase_signal TEXT,
            predicted_next_purchase_date TEXT,
            avg_days_between_orders DOUBLE,
            avg_order_spend DOUBLE,
            discount_sensitivity TEXT,
            cancel_rate DOUBLE,
            last_purchased_sku TEXT,
            top_affinity_product TEXT,
            second_affinity_product TEXT,
            channel_preference TEXT,
            lifetime_contribution_margin DOUBLE,
            is_margin_negative BOOLEAN,
            source_contact_quality TEXT,
            contact_quality TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.dim_customers VALUES
          ('key-cust-001', 1001, 'C001', 'Nguyen Van A', '0901000001',
           'a@test.vn', 'Retail', '2023-01-10',
           'VIP', 'active', 'DUE_SOON', '2026-06-20',
           14.5, 850000.0, 'LOW', 0.02,
           'SKU-A', 'SKU-B', 'SKU-C', 'online',
           1200000.0, false, 'unverified', 'unverified'),
          ('key-cust-002', 1002, 'C002', 'Tran Thi B', '0902000002',
           'b@test.vn', 'Wholesale', '2022-05-15',
           'GOLD', 'at_risk', 'OVERDUE', '2026-06-10',
           30.0, 2000000.0, 'HIGH', 0.10,
           'SKU-D', 'SKU-E', NULL, 'store',
           800000.0, false, 'unverified', 'unverified')
    """)

    # mart_product_health
    conn.execute("""
        CREATE TABLE main_marts.mart_product_health (
            product_key TEXT,
            sku TEXT,
            abc_class TEXT,
            health_class TEXT,
            lifecycle_stage TEXT,
            velocity_momentum TEXT,
            oos_risk TEXT,
            realized_margin_pct DOUBLE,
            discount_dependency TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.mart_product_health VALUES
          ('pk-001', 'SKU-A', 'A', 'STAR', 'growth', 'accelerating', 'LOW', 0.35, 'LOW'),
          ('pk-002', 'SKU-B', 'B', 'CASH_COW', 'mature', 'stable', 'MEDIUM', 0.25, 'MEDIUM')
    """)

    # mart_customer_action_queue
    # Note: duckdb_reader aliases action_rationale→rationale_vi, value_at_stake→value_at_stake_vnd,
    # priority_rank→priority, queue_generated_at→generated_date
    conn.execute("""
        CREATE TABLE main_marts.mart_customer_action_queue (
            customer_key TEXT,
            action_type TEXT,
            action_rationale TEXT,
            value_at_stake BIGINT,
            priority_rank INTEGER,
            queue_generated_at DATE
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.mart_customer_action_queue VALUES
          ('key-cust-001', 'REORDER_NUDGE',
           'Khách sắp đến chu kỳ mua', 850000, 1, '2026-06-14'),
          ('key-cust-002', 'WIN_BACK',
           'Khách chưa mua 45 ngày', 2000000, 2, '2026-06-14')
    """)

    # dim_products
    # Note: duckdb_reader aliases brand_name→brand, last_sold_price→unit_price
    conn.execute("""
        CREATE TABLE main_marts.dim_products (
            product_key TEXT,
            sku TEXT,
            variant_id BIGINT,
            product_name TEXT,
            brand_name TEXT,
            last_sold_price DOUBLE,
            is_active BOOLEAN
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.dim_products VALUES
          ('pk-001', 'SKU-A', 10001, 'Kem Duong Am A', 'BrandX', 250000.0, true),
          ('pk-002', 'SKU-B', 10002, 'Serum Trang Da B', 'BrandY', 450000.0, true)
    """)

    # dim_channels — needed by fetch_order_hdr JOIN
    conn.execute("""
        CREATE TABLE main_marts.dim_channels (
            channel_key TEXT,
            channel_name TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.dim_channels VALUES
          ('ch-online', 'online'),
          ('ch-store', 'store')
    """)

    # fact_orders — uses customer_key (MD5) and channel_key, not customer_id/channel directly
    conn.execute("""
        CREATE TABLE main_marts.fact_orders (
            order_id TEXT,
            order_code TEXT,
            customer_key TEXT,
            channel_key TEXT,
            date_key INTEGER,
            net_revenue BIGINT,
            status TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.fact_orders VALUES
          ('ord-001', 'HD001', 'key-cust-001', 'ch-online', 20260101, 850000, 'completed'),
          ('ord-002', 'HD002', 'key-cust-002', 'ch-store',  20260201, 2000000, 'completed'),
          ('ord-003', 'HD003', 'key-cust-001', 'ch-online', 20260601, 500000, 'completed')
    """)

    conn.close()
    # Re-open read-only as production code does.
    return duckdb.connect(path, read_only=True)


@pytest.fixture()
def tmp_dirs() -> Generator[tuple[str, str], None, None]:
    """Yield (olap_duckdb_path, cache_db_path) in a temp directory."""
    with tempfile.TemporaryDirectory() as d:
        yield os.path.join(d, "olap.duckdb"), os.path.join(d, "cache.db")


@pytest.fixture()
def warehouse_and_cache(tmp_dirs):
    """Return (olap_conn, cache_db_path) using the synthetic fixture."""
    olap_path, cache_path = tmp_dirs
    conn = _make_warehouse(olap_path)
    yield conn, cache_path
    conn.close()


# ─── T1: rows land in every wh_* table ───────────────────────────────────────

def test_t1_all_tables_populated(warehouse_and_cache):
    olap_conn, cache_path = warehouse_and_cache
    run(olap_conn=olap_conn, cache_db=cache_path)

    db = sqlite3.connect(cache_path)
    try:
        checks = {
            "wh_customer_insight": 2,
            "wh_product_insight": 2,
            "wh_action_queue": 2,
            "wh_customer_base": 2,
            "wh_product": 2,
            "wh_order_hdr": 3,
            "wh_party_seed": 2,
        }
        for table, expected in checks.items():
            count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == expected, f"{table}: expected {expected} rows, got {count}"
    finally:
        db.close()


# ─── T2: idempotent — run twice, counts IDENTICAL (no row growth) ────────────

def test_t2_idempotent(warehouse_and_cache):
    olap_conn, cache_path = warehouse_and_cache

    _wh_tables = [
        "wh_customer_insight", "wh_product_insight", "wh_action_queue",
        "wh_customer_base", "wh_product", "wh_order_hdr", "wh_party_seed",
    ]

    run(olap_conn=olap_conn, cache_db=cache_path)

    # Capture exact counts after run-1.
    db = sqlite3.connect(cache_path)
    try:
        counts_after_run1 = {
            t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in _wh_tables
        }
    finally:
        db.close()

    run(olap_conn=olap_conn, cache_db=cache_path)

    # Assert each table's count is IDENTICAL after run-2 — no growth permitted.
    db = sqlite3.connect(cache_path)
    try:
        for table in _wh_tables:
            count_run2 = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count_run2 == counts_after_run1[table], (
                f"{table}: count changed from {counts_after_run1[table]} "
                f"after run-1 to {count_run2} after run-2 (not idempotent)"
            )
    finally:
        db.close()


# ─── T3: wh_party_seed populated ─────────────────────────────────────────────

def test_t3_party_seed_populated(warehouse_and_cache):
    olap_conn, cache_path = warehouse_and_cache
    run(olap_conn=olap_conn, cache_db=cache_path)

    db = sqlite3.connect(cache_path)
    try:
        rows = db.execute(
            "SELECT customer_id, customer_key FROM wh_party_seed ORDER BY customer_id"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0] == (1001, "key-cust-001")
        assert rows[1] == (1002, "key-cust-002")
    finally:
        db.close()


# ─── T4: wh_sync_run logged with status='ok' ─────────────────────────────────

def test_t4_sync_run_logged_ok(warehouse_and_cache):
    olap_conn, cache_path = warehouse_and_cache
    run(olap_conn=olap_conn, cache_db=cache_path)

    db = sqlite3.connect(cache_path)
    try:
        rows = db.execute(
            "SELECT source_table, status FROM wh_sync_run ORDER BY source_table"
        ).fetchall()
        statuses = {r[0]: r[1] for r in rows}

        expected_tables = [
            "wh_customer_insight", "wh_product_insight", "wh_action_queue",
            "wh_customer_base", "wh_product", "wh_order_hdr", "wh_party_seed",
        ]
        for t in expected_tables:
            assert t in statuses, f"wh_sync_run missing entry for {t}"
            assert statuses[t] == "ok", f"{t}: status={statuses[t]}, want ok"
    finally:
        db.close()


# ─── T5: incremental — second run with higher HWM loads only new orders ───────

def test_t5_incremental_order_hdr(tmp_dirs):
    olap_path, cache_path = tmp_dirs

    # First run: warehouse has 2 old orders.
    conn = duckdb.connect(olap_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts")
    _create_minimal_dim_tables(conn)
    conn.execute("""
        CREATE TABLE main_marts.fact_orders (
            order_id TEXT, order_code TEXT, customer_key TEXT, channel_key TEXT,
            date_key INTEGER, net_revenue BIGINT, status TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.fact_orders VALUES
          ('ord-A', 'HA001', 'key-c1', 'ch-online', 20260101, 100000, 'completed'),
          ('ord-B', 'HA002', 'key-c1', 'ch-online', 20260201, 200000, 'completed')
    """)
    conn.close()

    ro1 = duckdb.connect(olap_path, read_only=True)
    run(olap_conn=ro1, cache_db=cache_path)
    ro1.close()

    db = sqlite3.connect(cache_path)
    count_after_run1 = db.execute("SELECT COUNT(*) FROM wh_order_hdr").fetchone()[0]
    db.close()
    assert count_after_run1 == 2

    # Second run: add one new order with a higher date_key.
    conn2 = duckdb.connect(olap_path)
    conn2.execute(
        "INSERT INTO main_marts.fact_orders VALUES "
        "('ord-C', 'HA003', 'key-c1', 'ch-online', 20260601, 300000, 'completed')"
    )
    conn2.close()

    ro2 = duckdb.connect(olap_path, read_only=True)
    run(olap_conn=ro2, cache_db=cache_path)
    ro2.close()

    db = sqlite3.connect(cache_path)
    count_after_run2 = db.execute("SELECT COUNT(*) FROM wh_order_hdr").fetchone()[0]
    db.close()
    # Should now have 3 total (2 old + 1 new).
    assert count_after_run2 == 3, f"Expected 3 orders after incremental run, got {count_after_run2}"


# ─── T6: missing-column fixture → MissingColumnError ─────────────────────────

def test_t6_missing_column_raises(tmp_dirs):
    olap_path, cache_path = tmp_dirs

    conn = duckdb.connect(olap_path)
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts")
    # dim_customers missing 'value_group' → must trigger MissingColumnError.
    conn.execute("""
        CREATE TABLE main_marts.dim_customers (
            customer_key TEXT,
            customer_id BIGINT
            -- intentionally missing all insight + base columns
        )
    """)
    conn.execute("INSERT INTO main_marts.dim_customers VALUES ('k1', 1)")
    conn.close()

    ro = duckdb.connect(olap_path, read_only=True)
    try:
        with pytest.raises(MissingColumnError):
            dr.fetch_customer_insight(ro)
    finally:
        ro.close()


# ─── helpers used by T5 ───────────────────────────────────────────────────────

def _create_minimal_dim_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create minimal mart tables needed by the full pipeline (except fact_orders)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_marts.dim_customers (
            customer_key TEXT, customer_id BIGINT, customer_code TEXT,
            full_name TEXT, phone TEXT, email TEXT, customer_group TEXT,
            first_order_date DATE, value_group TEXT, customer_status TEXT,
            next_purchase_signal TEXT, predicted_next_purchase_date TEXT,
            avg_days_between_orders DOUBLE, avg_order_spend DOUBLE,
            discount_sensitivity TEXT, cancel_rate DOUBLE, last_purchased_sku TEXT,
            top_affinity_product TEXT, second_affinity_product TEXT,
            channel_preference TEXT, lifetime_contribution_margin DOUBLE,
            is_margin_negative BOOLEAN,
            source_contact_quality TEXT, contact_quality TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.dim_customers VALUES
          ('key-c1', 1001, 'C1', 'Test', '0901', 't@t.vn', 'R', '2023-01-01',
           'VIP', 'active', 'DUE_SOON', NULL, 14.0, 500000.0, 'LOW', 0.01,
           'S1', 'S2', NULL, 'online', 500000.0, false, 'unverified', 'unverified')
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_marts.mart_product_health (
            product_key TEXT, sku TEXT, abc_class TEXT, health_class TEXT,
            lifecycle_stage TEXT, velocity_momentum TEXT, oos_risk TEXT,
            realized_margin_pct DOUBLE, discount_dependency TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_marts.mart_customer_action_queue (
            customer_key TEXT, action_type TEXT, action_rationale TEXT,
            value_at_stake BIGINT, priority_rank INTEGER, queue_generated_at DATE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_marts.dim_products (
            product_key TEXT, sku TEXT, variant_id BIGINT, product_name TEXT,
            brand_name TEXT, last_sold_price DOUBLE, is_active BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_marts.dim_channels (
            channel_key TEXT, channel_name TEXT
        )
    """)
    conn.execute("""
        INSERT INTO main_marts.dim_channels VALUES ('ch-online', 'online')
    """)
