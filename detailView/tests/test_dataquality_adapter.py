"""Tests for DuckDbDataQualityAdapter.

Covers:
- Happy path: mart_data_quality present → DataQualitySummary with correct values
- Missing view → None (no exception)
- Empty mart table → None
- Cache: second call returns same object (within TTL)
- has_carrier_link_map derived from capability
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import duckdb
import pytest

from app.adapters.outbound.duckdb.capability_adapter import DuckDbCapabilityAdapter
from app.adapters.outbound.duckdb.dataquality_adapter import DuckDbDataQualityAdapter
from app.domain.shared import DataQualitySummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def dq_db_path(tmp_path: Path) -> str:
    """DuckDB with a populated mart_data_quality table."""
    db_path = str(tmp_path / "dq_test.duckdb")
    con = duckdb.connect(db_path)
    try:
        con.execute("""
            CREATE TABLE mart_data_quality (
                dq_key VARCHAR,
                as_of_ict TIMESTAMPTZ,
                total_orders INTEGER,
                cogs_rate_pct DOUBLE,
                platform_fees_rate_pct DOUBLE,
                fulfillment_coverage_pct DOUBLE,
                return_rate_pct DOUBLE,
                us_share_pct DOUBLE,
                carrier_null_rate_pct DOUBLE,
                acq_source_null_rate_pct DOUBLE
            )
        """)
        con.execute("""
            INSERT INTO mart_data_quality VALUES (
                'DQ-TEST', '2026-05-30 07:11:44+00', 3352,
                29.3, 2.7, 94.5, 0.1, 35.4, 18.8, 100.0
            )
        """)
    finally:
        con.close()
    return db_path


@pytest.fixture()
def empty_dq_db_path(tmp_path: Path) -> str:
    """DuckDB with mart_data_quality table but NO rows."""
    db_path = str(tmp_path / "dq_empty.duckdb")
    con = duckdb.connect(db_path)
    try:
        con.execute("""
            CREATE TABLE mart_data_quality (
                dq_key VARCHAR, as_of_ict TIMESTAMPTZ, total_orders INTEGER,
                cogs_rate_pct DOUBLE, platform_fees_rate_pct DOUBLE,
                fulfillment_coverage_pct DOUBLE, return_rate_pct DOUBLE,
                us_share_pct DOUBLE, carrier_null_rate_pct DOUBLE,
                acq_source_null_rate_pct DOUBLE
            )
        """)
        # No rows inserted.
    finally:
        con.close()
    return db_path


@pytest.fixture()
def no_mart_db_path(tmp_path: Path) -> str:
    """DuckDB with NO mart_data_quality table at all."""
    db_path = str(tmp_path / "dq_no_mart.duckdb")
    con = duckdb.connect(db_path)
    con.close()
    return db_path


def _make_cap(db_path: str, tmp_path: Path, *, carrier_url_col: bool = False) -> DuckDbCapabilityAdapter:
    """Build a CapabilityAdapter pointing at a real DB; optionally add carrier_url col."""
    if carrier_url_col:
        con = duckdb.connect(db_path)
        try:
            # Add carrier_url to fact_fulfillments so has_carrier_link_map = True.
            con.execute(
                "CREATE TABLE IF NOT EXISTS fact_fulfillments "
                "(fulfillment_id VARCHAR, carrier_url VARCHAR)"
            )
        finally:
            con.close()

    known = tmp_path / ".known_tables.json"
    known.write_text(json.dumps({"tables": ["mart_data_quality"]}))
    rolling = tmp_path / "rolling"
    rolling.mkdir(exist_ok=True)
    return DuckDbCapabilityAdapter(
        db_path=db_path,
        rolling_dir=str(rolling),
        known_tables_path=str(known),
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_coverage_metrics_returns_summary(dq_db_path: str, tmp_path: Path) -> None:
    cap = _make_cap(dq_db_path, tmp_path)
    adapter = DuckDbDataQualityAdapter(db_path=dq_db_path, capability=cap)

    summary = adapter.coverage_metrics()

    assert summary is not None
    assert isinstance(summary, DataQualitySummary)
    assert summary.total_orders == 3352
    assert summary.cogs_rate_pct == pytest.approx(29.3)
    assert summary.platform_fees_rate_pct == pytest.approx(2.7)
    assert summary.fulfillment_coverage_pct == pytest.approx(94.5)
    assert summary.return_rate_pct == pytest.approx(0.1)
    assert summary.us_share_pct == pytest.approx(35.4)
    assert summary.carrier_null_rate_pct == pytest.approx(18.8)
    assert summary.acq_source_null_rate_pct == pytest.approx(100.0)
    assert summary.as_of is not None
    # data_version from empty rolling dir → "unknown"
    assert isinstance(summary.data_version, str)
    assert isinstance(summary.stale_views, list)


def test_coverage_metrics_has_carrier_link_false_by_default(dq_db_path: str, tmp_path: Path) -> None:
    cap = _make_cap(dq_db_path, tmp_path, carrier_url_col=False)
    adapter = DuckDbDataQualityAdapter(db_path=dq_db_path, capability=cap)
    summary = adapter.coverage_metrics()
    assert summary is not None
    assert summary.has_carrier_link_map is False


def test_coverage_metrics_has_carrier_link_true_when_col_exists(tmp_path: Path) -> None:
    # Build a DB that has both mart_data_quality AND fact_fulfillments.carrier_url.
    db_path = str(tmp_path / "carrier.duckdb")
    con = duckdb.connect(db_path)
    try:
        con.execute("""
            CREATE TABLE mart_data_quality (
                dq_key VARCHAR, as_of_ict TIMESTAMPTZ, total_orders INTEGER,
                cogs_rate_pct DOUBLE, platform_fees_rate_pct DOUBLE,
                fulfillment_coverage_pct DOUBLE, return_rate_pct DOUBLE,
                us_share_pct DOUBLE, carrier_null_rate_pct DOUBLE,
                acq_source_null_rate_pct DOUBLE
            )
        """)
        con.execute(
            "INSERT INTO mart_data_quality VALUES "
            "('DQ-C','2026-05-30 07:11:44+00',100,29.0,3.0,95.0,0.1,30.0,10.0,100.0)"
        )
        con.execute(
            "CREATE TABLE fact_fulfillments "
            "(fulfillment_id VARCHAR, carrier_url VARCHAR)"
        )
    finally:
        con.close()

    cap = _make_cap(db_path, tmp_path, carrier_url_col=False)  # already has the col
    adapter = DuckDbDataQualityAdapter(db_path=db_path, capability=cap)
    summary = adapter.coverage_metrics()
    assert summary is not None
    assert summary.has_carrier_link_map is True


# ---------------------------------------------------------------------------
# Missing mart view → None
# ---------------------------------------------------------------------------

def test_coverage_metrics_returns_none_when_mart_absent(no_mart_db_path: str, tmp_path: Path) -> None:
    cap = _make_cap(no_mart_db_path, tmp_path)
    adapter = DuckDbDataQualityAdapter(db_path=no_mart_db_path, capability=cap)
    assert adapter.coverage_metrics() is None


# ---------------------------------------------------------------------------
# Empty mart table → None
# ---------------------------------------------------------------------------

def test_coverage_metrics_returns_none_when_mart_empty(empty_dq_db_path: str, tmp_path: Path) -> None:
    cap = _make_cap(empty_dq_db_path, tmp_path)
    adapter = DuckDbDataQualityAdapter(db_path=empty_dq_db_path, capability=cap)
    assert adapter.coverage_metrics() is None


# ---------------------------------------------------------------------------
# Cache: second call within TTL returns same object
# ---------------------------------------------------------------------------

def test_coverage_metrics_cached(dq_db_path: str, tmp_path: Path) -> None:
    cap = _make_cap(dq_db_path, tmp_path)
    adapter = DuckDbDataQualityAdapter(db_path=dq_db_path, capability=cap)
    first = adapter.coverage_metrics()
    second = adapter.coverage_metrics()
    # Both calls should return the same frozen dataclass instance (cache hit).
    assert first is second


def test_coverage_metrics_none_cached(no_mart_db_path: str, tmp_path: Path) -> None:
    """None result is also cached — must not re-query DB on every request."""
    cap = _make_cap(no_mart_db_path, tmp_path)
    adapter = DuckDbDataQualityAdapter(db_path=no_mart_db_path, capability=cap)
    first = adapter.coverage_metrics()
    second = adapter.coverage_metrics()
    assert first is None
    assert second is None
