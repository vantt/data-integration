"""Tests for DuckDbCapabilityAdapter against a temp DuckDB + temp rolling dir.

Covers:
- has_column / view_exists against information_schema
- data_version from filesystem parquet filenames
- freshness from parquet mtime
- known_tables from .known_tables.json
- stale_views threshold logic
- graceful degradation when DB is absent / dir is missing
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import duckdb
import pytest

from app.adapters.outbound.duckdb.capability_adapter import DuckDbCapabilityAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_db(tmp_path: Path) -> str:
    """In-memory-style: a real file DB with a minimal table for introspection."""
    db_path = str(tmp_path / "cap_test.duckdb")
    con = duckdb.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE fact_fulfillments ("
            "fulfillment_id VARCHAR, carrier_id VARCHAR, tracking_code VARCHAR)"
        )
        con.execute("CREATE TABLE dim_channels (channel_key VARCHAR, channel_name VARCHAR)")
    finally:
        con.close()
    return db_path


@pytest.fixture()
def rolling_dir(tmp_path: Path) -> Path:
    """Temp rolling parquet directory with two table subdirs."""
    rd = tmp_path / "rolling"
    rd.mkdir()

    # fact_orders dir — two parquet files; the second (later) basename wins.
    fo = rd / "fact_orders"
    fo.mkdir()
    (fo / "fact_orders_20260529060000.parquet").write_bytes(b"fake")
    (fo / "fact_orders_20260530071144.parquet").write_bytes(b"fake")

    # mart_sku_economics_monthly dir — one parquet with a larger basename (later date).
    ms = rd / "mart_sku_economics_monthly"
    ms.mkdir()
    (ms / "mart_sku_economics_monthly_20260530071144.parquet").write_bytes(b"fake")

    return rd


@pytest.fixture()
def known_tables_path(tmp_path: Path, rolling_dir: Path) -> str:
    kt = tmp_path / ".known_tables.json"
    kt.write_text(json.dumps({"tables": ["fact_orders", "fact_fulfillments"]}))
    return str(kt)


@pytest.fixture()
def adapter(mem_db: str, rolling_dir: Path, known_tables_path: str) -> DuckDbCapabilityAdapter:
    return DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(rolling_dir),
        known_tables_path=known_tables_path,
    )


# ---------------------------------------------------------------------------
# has_column / view_exists
# ---------------------------------------------------------------------------

def test_has_column_true(adapter: DuckDbCapabilityAdapter) -> None:
    assert adapter.has_column("fact_fulfillments", "carrier_id") is True


def test_has_column_false_missing_column(adapter: DuckDbCapabilityAdapter) -> None:
    # carrier_url does NOT exist in the seeded schema.
    assert adapter.has_column("fact_fulfillments", "carrier_url") is False


def test_has_column_false_missing_table(adapter: DuckDbCapabilityAdapter) -> None:
    assert adapter.has_column("nonexistent_view", "any_col") is False


def test_view_exists_true(adapter: DuckDbCapabilityAdapter) -> None:
    assert adapter.view_exists("fact_fulfillments") is True
    assert adapter.view_exists("dim_channels") is True


def test_view_exists_false(adapter: DuckDbCapabilityAdapter) -> None:
    assert adapter.view_exists("dim_carriers") is False


# ---------------------------------------------------------------------------
# data_version
# ---------------------------------------------------------------------------

def test_data_version_returns_max_basename(adapter: DuckDbCapabilityAdapter) -> None:
    version = adapter.data_version()
    # mart_sku_economics_monthly_20260530071144 > fact_orders_20260530071144 lexically
    # because 'm' > 'f'.
    assert version.endswith(".parquet")
    assert "20260530071144" in version


def test_data_version_unknown_when_dir_missing(tmp_path: Path, mem_db: str, known_tables_path: str) -> None:
    cap = DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(tmp_path / "nonexistent"),
        known_tables_path=known_tables_path,
    )
    assert cap.data_version() == "unknown"


def test_data_version_unknown_when_no_parquet_files(tmp_path: Path, mem_db: str, known_tables_path: str) -> None:
    empty_rd = tmp_path / "empty_rolling"
    empty_rd.mkdir()
    (empty_rd / "fact_orders").mkdir()  # subdir exists but no .parquet files
    cap = DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(empty_rd),
        known_tables_path=known_tables_path,
    )
    assert cap.data_version() == "unknown"


# ---------------------------------------------------------------------------
# freshness
# ---------------------------------------------------------------------------

def test_freshness_returns_datetime(adapter: DuckDbCapabilityAdapter) -> None:
    dt = adapter.freshness("fact_orders")
    assert dt is not None
    # Should be close to now (the file was just written in the fixture).
    assert abs(time.time() - dt.timestamp()) < 60


def test_freshness_none_for_missing_dir(adapter: DuckDbCapabilityAdapter) -> None:
    assert adapter.freshness("nonexistent_table") is None


def test_freshness_none_for_empty_dir(tmp_path: Path, mem_db: str, known_tables_path: str) -> None:
    rd = tmp_path / "rolling2"
    rd.mkdir()
    (rd / "fact_orders").mkdir()  # dir exists but no parquet
    cap = DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(rd),
        known_tables_path=known_tables_path,
    )
    assert cap.freshness("fact_orders") is None


# ---------------------------------------------------------------------------
# known_tables
# ---------------------------------------------------------------------------

def test_known_tables_returns_frozenset(adapter: DuckDbCapabilityAdapter) -> None:
    tables = adapter.known_tables()
    assert isinstance(tables, frozenset)
    assert "fact_orders" in tables
    assert "fact_fulfillments" in tables


def test_known_tables_empty_when_file_missing(tmp_path: Path, mem_db: str, rolling_dir: Path) -> None:
    cap = DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(rolling_dir),
        known_tables_path=str(tmp_path / "nonexistent.json"),
    )
    assert cap.known_tables() == frozenset()


# ---------------------------------------------------------------------------
# stale_views
# ---------------------------------------------------------------------------

def test_stale_views_detects_old_parquet(tmp_path: Path, mem_db: str, known_tables_path: str) -> None:
    rd = tmp_path / "rolling_stale"
    rd.mkdir()

    # fact_orders: fresh (mtime = now)
    fresh_dir = rd / "fact_orders"
    fresh_dir.mkdir()
    fresh_file = fresh_dir / "fact_orders_20260530071144.parquet"
    fresh_file.write_bytes(b"fake")

    # dim_product_category: stale (mtime backdated to > 48 h ago)
    stale_dir = rd / "dim_product_category"
    stale_dir.mkdir()
    stale_file = stale_dir / "dim_product_category_20260201180435.parquet"
    stale_file.write_bytes(b"fake")
    # Set mtime to 96 hours ago.
    old_time = time.time() - 96 * 3600
    os.utime(str(stale_file), (old_time, old_time))

    cap = DuckDbCapabilityAdapter(
        db_path=mem_db,
        rolling_dir=str(rd),
        known_tables_path=known_tables_path,
    )
    stale = cap.stale_views(threshold_hours=48.0)
    assert "dim_product_category" in stale
    assert "fact_orders" not in stale


# ---------------------------------------------------------------------------
# Graceful degradation: DB absent
# ---------------------------------------------------------------------------

def test_schema_degrades_gracefully_when_db_absent(tmp_path: Path, rolling_dir: Path, known_tables_path: str) -> None:
    cap = DuckDbCapabilityAdapter(
        db_path=str(tmp_path / "nonexistent.duckdb"),
        rolling_dir=str(rolling_dir),
        known_tables_path=known_tables_path,
    )
    # Should not raise; returns False / empty rather than crashing.
    assert cap.view_exists("fact_orders") is False
    assert cap.has_column("fact_orders", "order_id") is False
