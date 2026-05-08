"""KPI Closure (Phase 5) — Revenue invariant check.

Daily 04:45 asset comparing Sapo source revenue vs warehouse fact_orders.
Writes to ingestion_health.duckdb with asset_key='kpi/revenue_daily'.

Gated behind KPI_CLOSURE_ENABLED=1 env flag (disabled by default).

Architecture:
- Source: raw__sapo.order → SUM($.total) for orders with created_on in [yesterday, today) UTC
- Warehouse: serving DB → SUM(net_revenue) from fact_orders WHERE date_key = yesterday (UTC)
- Drift: (warehouse - source) / source

Note: source reads raw DuckDB (not live Sapo API) so both sides derive from the same ingested
data. This catches transformation errors rather than ingestion gaps; RECON_LIVE_API not needed.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import duckdb
from dagster import asset, MetadataValue, Output

from orchestration.ops.ingestion_health import record_run, get_db_path

logger = logging.getLogger(__name__)

# Feature flag — disabled by default until calibration complete
_KPI_ENABLED = os.environ.get("KPI_CLOSURE_ENABLED", "").strip() == "1"

# DB paths — must match reconciliation.py / bootstrap_serving_views.py
_DATA_LAKE = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
_SAPO_ORDER_PATH = os.path.join(_DATA_LAKE, "sapo_raw", "order")
_SERVING_DB_PATH = os.path.join(_DATA_LAKE, "serving", "olap.duckdb")

# Statuses to exclude from revenue calculation
_EXCLUDE_STATUSES = ["cancelled", "voided"]


def _make_run_id() -> str:
    return str(uuid.uuid4())


def _yesterday_window_utc() -> tuple[datetime, datetime, int]:
    """Return (yesterday_00:00 UTC, today_00:00 UTC, date_key YYYYMMDD).

    Both source and warehouse use UTC for consistency:
    - raw__sapo.order: $.created_on cast as TIMESTAMPTZ (UTC-aware comparison)
    - fact_orders.date_key: strftime(created_at) uses DuckDB default timezone (UTC)
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    # date_key = UTC date of the query window (matches fact_orders.date_key logic)
    date_key = int(yesterday_start.strftime("%Y%m%d"))
    return yesterday_start, today_start, date_key


def _fetch_sapo_revenue(window_start: datetime, window_end: datetime) -> Optional[float]:
    """Fetch sum of order revenue from sapo_raw/order parquet files for orders created in [window_start, window_end).

    Reads raw parquet (not live Sapo API) so the comparison isolates transformation errors.
    The Sapo orders API ignores created_on filtering and returns all historical orders.
    Deduplicates entity_id by taking the latest event_timestamp per order.
    """
    if not _KPI_ENABLED:
        logger.debug("kpi_closure: KPI_CLOSURE_ENABLED not set — skipping source revenue")
        return None

    if not os.path.exists(_SAPO_ORDER_PATH):
        logger.warning("kpi_closure: sapo raw order dir not found at %s", _SAPO_ORDER_PATH)
        return None

    conn = None
    try:
        conn = duckdb.connect()
        # Partition glob avoids _delta_log checkpoint parquets
        parquet_glob = _SAPO_ORDER_PATH.replace("\\", "/") + "/ingest_method=*/**/*.parquet"
        exclude_list = ", ".join(f"'{s}'" for s in _EXCLUDE_STATUSES)
        row = conn.execute(
            f"""
            WITH latest AS (
                SELECT entity_id, payload,
                    ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY event_timestamp DESC) AS rn
                FROM read_parquet('{parquet_glob}', union_by_name=true, hive_partitioning=true)
                WHERE TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) >= ?
                  AND TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) < ?
            )
            SELECT COALESCE(SUM(CAST(json_extract_string(payload, '$.total') AS DOUBLE)), 0)
            FROM latest
            WHERE rn = 1
              AND LOWER(json_extract_string(payload, '$.status')) NOT IN ({exclude_list})
            """,
            [window_start, window_end],
        ).fetchone()
        return float(row[0]) if row else 0.0
    except Exception as exc:
        logger.error("kpi_closure: raw revenue query failed — %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def _fetch_warehouse_revenue(date_key: int) -> Optional[float]:
    """Fetch SUM(net_revenue) from fact_orders for the given date_key."""
    if not os.path.exists(_SERVING_DB_PATH):
        logger.warning("kpi_closure: serving DB not found at %s", _SERVING_DB_PATH)
        return None

    conn = None
    try:
        conn = duckdb.connect(_SERVING_DB_PATH, read_only=True)
        # Exclude cancelled/voided orders
        exclude_list = ", ".join(f"'{s}'" for s in _EXCLUDE_STATUSES)
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(net_revenue), 0)
            FROM fact_orders
            WHERE date_key = ?
              AND LOWER(status) NOT IN ({exclude_list})
            """,
            [date_key],
        ).fetchone()
        return float(row[0]) if row else 0.0
    except Exception as exc:
        logger.error("kpi_closure: warehouse query failed — %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def _compute_drift(source: Optional[float], dest: Optional[float]) -> Optional[float]:
    """drift_pct = (dest - source) / source. Returns None if source unknown or zero."""
    if source is None or source == 0:
        return None
    if dest is None:
        return None
    return (dest - source) / source


def _persist_kpi(
    asset_key: str,
    run_id: str,
    started: datetime,
    source_revenue: Optional[float],
    warehouse_revenue: Optional[float],
    drift_pct: Optional[float],
    date_key: int,
    status: str = "success",
) -> None:
    """Write KPI closure result to ingestion_health.duckdb."""
    metadata = {
        "source_revenue": source_revenue,
        "warehouse_revenue": warehouse_revenue,
        "drift_pct": drift_pct,
        "date_key": date_key,
        "currency": "VND",
    }
    try:
        record_run(
            asset_key=asset_key,
            run_id=run_id,
            run_started_at=started,
            run_ended_at=datetime.now(timezone.utc),
            status=status,
            rows_fetched=None,
            rows_written=None,
            metadata=metadata,
        )
    except Exception:
        logger.warning("_persist_kpi(%s): failed to write health record", asset_key, exc_info=True)


@asset(group_name="kpi_closure", key_prefix=["kpi"])
def kpi_revenue_daily(context):
    """Daily revenue invariant check: raw DB source vs warehouse fact_orders.

    Compares yesterday's revenue between:
    - Source: raw__sapo.order SUM($.total) for created_on in [yesterday, today) UTC
    - Warehouse: SUM(net_revenue) from fact_orders WHERE date_key = yesterday (UTC)

    Gated behind KPI_CLOSURE_ENABLED=1. RECON_LIVE_API not required.
    """
    started = datetime.now(timezone.utc)
    run_id = _make_run_id()
    asset_key = "kpi/revenue_daily"
    window_start, window_end, date_key = _yesterday_window_utc()

    source_revenue = _fetch_sapo_revenue(window_start, window_end)
    warehouse_revenue = _fetch_warehouse_revenue(date_key)
    drift_pct = _compute_drift(source_revenue, warehouse_revenue)

    # Determine status
    if not _KPI_ENABLED:
        status = "disabled"
    elif source_revenue is None and warehouse_revenue is None:
        status = "failed"  # both sides unavailable
    elif source_revenue is None:
        status = "partial_source"  # raw DB unavailable or query failed
    elif warehouse_revenue is None:
        status = "partial_warehouse"  # serving DB unavailable
    else:
        status = "success"

    context.log.info(
        "kpi_revenue_daily: date_key=%d source=%.2f warehouse=%.2f drift_pct=%s",
        date_key,
        source_revenue or 0,
        warehouse_revenue or 0,
        f"{drift_pct:.4%}" if drift_pct is not None else "N/A",
    )

    _persist_kpi(
        asset_key=asset_key,
        run_id=run_id,
        started=started,
        source_revenue=source_revenue,
        warehouse_revenue=warehouse_revenue,
        drift_pct=drift_pct,
        date_key=date_key,
        status=status,
    )

    return Output(
        value={
            "source_revenue": source_revenue,
            "warehouse_revenue": warehouse_revenue,
            "drift_pct": drift_pct,
            "date_key": date_key,
        },
        metadata={
            "date_key": MetadataValue.int(date_key),
            # MetadataValue.float() rejects int. `or 0` short-circuits to a Python int
            # when the left side is None/0.0 (falsy) — must use 0.0 explicitly.
            "source_revenue_vnd": MetadataValue.float(source_revenue or 0.0),
            "warehouse_revenue_vnd": MetadataValue.float(warehouse_revenue or 0.0),
            "drift_pct": MetadataValue.float(drift_pct * 100 if drift_pct is not None else 0.0),
            "kpi_enabled": MetadataValue.bool(_KPI_ENABLED),
            "window_start": MetadataValue.text(window_start.isoformat()),
            "window_end": MetadataValue.text(window_end.isoformat()),
        },
    )
