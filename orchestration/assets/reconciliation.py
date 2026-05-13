"""Dagster assets for source↔destination reconciliation (Phase 3).

Four daily assets compare external source truth vs warehouse row counts and
persist drift metrics to ingestion_health.duckdb under asset_key='recon/...'.

Asset group: reconciliation
Schedule: health_recon_daily_schedule at 04:30 Asia/Ho_Chi_Minh (registered in definitions.py)

Live Sapo API calls are gated behind RECON_LIVE_API=1 env flag.
File-drop recon reads ingestion_health.duckdb only — no xlsx re-parsing at recon time.
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Reconciliation window: trailing 7 days of ingestion runs
_WINDOW_DAYS = 7

# Raw DuckDB path (MISA/Shopee parquet-backed tables live here via dlt)
_DATA_LAKE = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
_RAW_DB_PATH = os.path.join(_DATA_LAKE, "raw", "raw.duckdb")

# asset_key strings used by Phase 1 ingestion assets in health DB
_SHOPEE_ASSET_KEY = "shopee/shopee_income_file_drop_asset"
_MISA_ASSET_KEY = "misa_amis/misa_sales_file_drop_asset"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_run_id() -> str:
    return str(uuid.uuid4())


def _window_utc(days: int = _WINDOW_DAYS) -> tuple[datetime, datetime]:
    """Return (window_start, window_end) in UTC — last `days` complete days."""
    now = datetime.now(timezone.utc)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    return start, end


_ICT = timezone(timedelta(hours=7))


def _yesterday_window_ict() -> tuple[datetime, datetime]:
    """Return (yesterday_ict_midnight, today_ict_midnight) as ICT-aware datetimes.

    Uses ICT (Asia/Ho_Chi_Minh, UTC+7) so that:
    - Sapo API receives ICT local strings (Sapo interprets bare datetimes as ICT)
    - Raw DB TIMESTAMPTZ comparison works correctly (DuckDB resolves +07:00 vs 'Z' internally)
    - Both source and dest count the same Vietnam business day
    """
    now_ict = datetime.now(_ICT)
    today_ict_midnight = now_ict.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_ict_midnight = today_ict_midnight - timedelta(days=1)
    return yesterday_ict_midnight, today_ict_midnight


def _compute_drift(source_count: Optional[int], dest_count: int) -> Optional[float]:
    """drift_pct = (dest - source) / source. Returns None if source is unknown."""
    if source_count is None or source_count == 0:
        return None
    return (dest_count - source_count) / source_count


def _persist_recon(
    asset_key: str,
    run_id: str,
    started: datetime,
    source_count: Optional[int],
    dest_count: int,
    drift_pct: Optional[float],
    window_start: datetime,
    window_end: datetime,
    status: str = "success",
) -> None:
    """Write one recon result row into ingestion_health.duckdb.

    Best-effort: lock contention or DB errors must not crash the recon asset.
    """
    metadata = {
        "source_count": source_count,
        "dest_count": dest_count,
        "drift_pct": drift_pct,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }
    try:
        record_run(
            asset_key=asset_key,
            run_id=run_id,
            run_started_at=started,
            run_ended_at=datetime.now(timezone.utc),
            status=status,
            rows_fetched=source_count,
            rows_written=dest_count,
            metadata=metadata,
        )
    except Exception:
        logger.warning("_persist_recon(%s): failed to write health record", asset_key, exc_info=True)


# ---------------------------------------------------------------------------
# File-drop recon helpers
# ---------------------------------------------------------------------------

def _file_drop_source_count(ingestion_asset_key: str, window_start: datetime) -> Optional[int]:
    """Sum rows_written from health DB for the given asset over the window.

    This uses Phase 1 records (rows_written = rows inserted from file).
    Returns None if no successful runs exist in the window.
    """
    try:
        conn = duckdb.connect(get_db_path(), read_only=True)
        row = conn.execute(
            """
            SELECT SUM(COALESCE(rows_written, 0))
            FROM ingestion_runs
            WHERE asset_key = ?
              AND status = 'success'
              AND run_started_at >= ?
            """,
            [ingestion_asset_key, window_start],
        ).fetchone()
        conn.close()
        if row and row[0] is not None:
            return int(row[0])
        return None
    except Exception as exc:
        logger.error("_file_drop_source_count: health DB query failed — %s", exc)
        return None


def _raw_table_dest_count(table_ref: str, window_start: datetime) -> Optional[int]:
    """Count rows in a raw DuckDB table loaded since window_start.

    Uses _dlt_load_time (a standard dlt-injected column) for time filtering.
    Falls back to full count if _dlt_load_time column is absent.
    """
    try:
        conn = duckdb.connect(_RAW_DB_PATH, read_only=True)
        # Check if _dlt_load_time exists (dlt standard)
        cols = [
            r[0]
            for r in conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = SPLIT_PART('{table_ref}', '.', 2)"
            ).fetchall()
        ]
        if "_dlt_load_time" in cols:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table_ref} WHERE _dlt_load_time >= ?",
                [window_start],
            ).fetchone()
        else:
            row = conn.execute(f"SELECT COUNT(*) FROM {table_ref}").fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as exc:
        logger.warning("_raw_table_dest_count: failed for %s — %s", table_ref, exc)
        return None


# ---------------------------------------------------------------------------
# File-drop reconciliation assets
# ---------------------------------------------------------------------------

@asset(group_name="reconciliation", key_prefix=["recon"])
def recon_shopee_daily(context):
    """Reconcile Shopee income file-drop: health DB rows_written vs raw table count.

    source_count = sum of rows_written in ingestion_health for shopee asset (last 7d)
    dest_count   = COUNT(*) from raw shopee table (last 7d via _dlt_load_time)
    """
    started = datetime.now(timezone.utc)
    run_id = _make_run_id()
    asset_key = "recon/shopee_daily"
    window_start, window_end = _window_utc()

    context.log.info("recon_shopee_daily: querying health DB source count...")
    source_count = _file_drop_source_count(_SHOPEE_ASSET_KEY, window_start)
    context.log.info("recon_shopee_daily: querying raw DuckDB dest count...")
    dest_count = _raw_table_dest_count("raw__shopee.order_revenue", window_start) or 0
    drift_pct = _compute_drift(source_count, dest_count)

    context.log.info(
        "recon_shopee_daily: source=%s dest=%d drift_pct=%s",
        source_count,
        dest_count,
        f"{drift_pct:.4f}" if drift_pct is not None else "N/A",
    )

    _persist_recon(
        asset_key=asset_key,
        run_id=run_id,
        started=started,
        source_count=source_count,
        dest_count=dest_count,
        drift_pct=drift_pct,
        window_start=window_start,
        window_end=window_end,
    )

    return Output(
        value={"source_count": source_count, "dest_count": dest_count, "drift_pct": drift_pct},
        metadata={
            "source_count": MetadataValue.int(source_count or -1),
            "dest_count": MetadataValue.int(dest_count),
            "drift_pct": MetadataValue.float(drift_pct if drift_pct is not None else 0.0),
            "window_days": MetadataValue.int(_WINDOW_DAYS),
        },
    )


@asset(group_name="reconciliation", key_prefix=["recon"])
def recon_misa_daily(context):
    """Reconcile MISA AMIS sales file-drop: health DB rows_written vs raw table count.

    source_count = sum of rows_written in ingestion_health for misa asset (last 7d)
    dest_count   = COUNT(*) from raw misa table (last 7d via _dlt_load_time)
    """
    started = datetime.now(timezone.utc)
    run_id = _make_run_id()
    asset_key = "recon/misa_daily"
    window_start, window_end = _window_utc()

    context.log.info("recon_misa_daily: querying health DB source count...")
    source_count = _file_drop_source_count(_MISA_ASSET_KEY, window_start)
    context.log.info("recon_misa_daily: querying raw DuckDB dest count...")
    dest_count = _raw_table_dest_count("raw__misa_amis.sales_lines", window_start) or 0
    drift_pct = _compute_drift(source_count, dest_count)

    context.log.info(
        "recon_misa_daily: source=%s dest=%d drift_pct=%s",
        source_count,
        dest_count,
        f"{drift_pct:.4f}" if drift_pct is not None else "N/A",
    )

    _persist_recon(
        asset_key=asset_key,
        run_id=run_id,
        started=started,
        source_count=source_count,
        dest_count=dest_count,
        drift_pct=drift_pct,
        window_start=window_start,
        window_end=window_end,
    )

    return Output(
        value={"source_count": source_count, "dest_count": dest_count, "drift_pct": drift_pct},
        metadata={
            "source_count": MetadataValue.int(source_count or -1),
            "dest_count": MetadataValue.int(dest_count),
            "drift_pct": MetadataValue.float(drift_pct if drift_pct is not None else 0.0),
            "window_days": MetadataValue.int(_WINDOW_DAYS),
        },
    )


# ---------------------------------------------------------------------------
# Sapo reconciliation assets
# ---------------------------------------------------------------------------

def _sapo_dest_count_orders(window_start: datetime, window_end: datetime) -> Optional[int]:
    """Count sapo orders in raw DB modified within [window_start, window_end)."""
    try:
        conn = duckdb.connect(_RAW_DB_PATH, read_only=True)
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT entity_id)
            FROM raw__sapo.order
            WHERE TRY_CAST(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ)
                  >= ? AND
                  TRY_CAST(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ)
                  < ?
            """,
            [window_start, window_end],
        ).fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as exc:
        logger.error("_sapo_dest_count_orders: raw DB query failed — %s", exc)
        return None


def _sapo_dest_count_customers(window_start: datetime, window_end: datetime) -> Optional[int]:
    """Count sapo customers created within [window_start, window_end)."""
    try:
        conn = duckdb.connect(_RAW_DB_PATH, read_only=True)
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT entity_id)
            FROM raw__sapo.customer
            WHERE TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ)
                  >= ? AND
                  TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ)
                  < ?
            """,
            [window_start, window_end],
        ).fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as exc:
        logger.error("_sapo_dest_count_customers: raw DB query failed — %s", exc)
        return None


@asset(group_name="reconciliation", key_prefix=["recon"])
def recon_sapo_orders_daily(context):
    """Reconcile Sapo orders: API metadata.total vs raw DB count (yesterday window).

    source_count = Sapo API metadata.total for modified_on in [yesterday, today) ICT
    dest_count   = COUNT(DISTINCT entity_id) in raw__sapo.order for same ICT window

    Live API call gated behind RECON_LIVE_API=1. When disabled, source_count=None
    and drift_pct=None — recon row is still written for Phase 4 visibility.
    """
    started = datetime.now(timezone.utc)
    run_id = _make_run_id()
    asset_key = "recon/sapo_orders_daily"
    window_start, window_end = _yesterday_window_ict()

    # Lazy import to avoid import-time Sapo side-effects
    try:
        from sapo.api_count import count_orders  # type: ignore[import]
    except ImportError:
        from ingestion.src.sapo.api_count import count_orders  # type: ignore[import]

    context.log.info("recon_sapo_orders_daily: calling Sapo API count_orders...")
    source_count = count_orders(window_start, window_end)
    context.log.info("recon_sapo_orders_daily: querying raw DuckDB dest count...")
    dest_count = _sapo_dest_count_orders(window_start, window_end) or 0
    drift_pct = _compute_drift(source_count, dest_count)

    context.log.info(
        "recon_sapo_orders_daily: source=%s dest=%d drift_pct=%s window=[%s, %s]",
        source_count,
        dest_count,
        f"{drift_pct:.4f}" if drift_pct is not None else "N/A",
        window_start.isoformat(),
        window_end.isoformat(),
    )

    _persist_recon(
        asset_key=asset_key,
        run_id=run_id,
        started=started,
        source_count=source_count,
        dest_count=dest_count,
        drift_pct=drift_pct,
        window_start=window_start,
        window_end=window_end,
        status="success" if source_count is not None else "partial",
    )

    return Output(
        value={"source_count": source_count, "dest_count": dest_count, "drift_pct": drift_pct},
        metadata={
            "source_count": MetadataValue.int(source_count if source_count is not None else -1),
            "dest_count": MetadataValue.int(dest_count),
            "drift_pct": MetadataValue.float(drift_pct if drift_pct is not None else 0.0),
            "window_start": MetadataValue.text(window_start.isoformat()),
            "window_end": MetadataValue.text(window_end.isoformat()),
            "live_api_enabled": MetadataValue.bool(
                __import__("os").environ.get("RECON_LIVE_API", "") == "1"
            ),
        },
    )


@asset(group_name="reconciliation", key_prefix=["recon"])
def recon_sapo_customers_daily(context):
    """Reconcile Sapo customers: API metadata.total vs raw DB count (yesterday window).

    source_count = Sapo API metadata.total for created_on in [yesterday, today) ICT
    dest_count   = COUNT(DISTINCT entity_id) in raw__sapo.customer for same ICT window

    NOTE: Sapo customers API filters on created_on only (no reliable modified_on).
    Live API call gated behind RECON_LIVE_API=1.
    """
    started = datetime.now(timezone.utc)
    run_id = _make_run_id()
    asset_key = "recon/sapo_customers_daily"
    window_start, window_end = _yesterday_window_ict()

    try:
        from sapo.api_count import count_customers  # type: ignore[import]
    except ImportError:
        from ingestion.src.sapo.api_count import count_customers  # type: ignore[import]

    context.log.info("recon_sapo_customers_daily: calling Sapo API count_customers...")
    source_count = count_customers(window_start, window_end)
    context.log.info("recon_sapo_customers_daily: querying raw DuckDB dest count...")
    dest_count = _sapo_dest_count_customers(window_start, window_end) or 0
    drift_pct = _compute_drift(source_count, dest_count)

    context.log.info(
        "recon_sapo_customers_daily: source=%s dest=%d drift_pct=%s window=[%s, %s]",
        source_count,
        dest_count,
        f"{drift_pct:.4f}" if drift_pct is not None else "N/A",
        window_start.isoformat(),
        window_end.isoformat(),
    )

    _persist_recon(
        asset_key=asset_key,
        run_id=run_id,
        started=started,
        source_count=source_count,
        dest_count=dest_count,
        drift_pct=drift_pct,
        window_start=window_start,
        window_end=window_end,
        status="success" if source_count is not None else "partial",
    )

    return Output(
        value={"source_count": source_count, "dest_count": dest_count, "drift_pct": drift_pct},
        metadata={
            "source_count": MetadataValue.int(source_count if source_count is not None else -1),
            "dest_count": MetadataValue.int(dest_count),
            "drift_pct": MetadataValue.float(drift_pct if drift_pct is not None else 0.0),
            "window_start": MetadataValue.text(window_start.isoformat()),
            "window_end": MetadataValue.text(window_end.isoformat()),
            "live_api_enabled": MetadataValue.bool(
                __import__("os").environ.get("RECON_LIVE_API", "") == "1"
            ),
        },
    )
