"""DuckDB implementation of DataQualityPort.

Reads from the mart_data_quality view (1 row, pipeline-refreshed) and merges
filesystem-derived signals from CapabilityAdapter into a DataQualitySummary.

Caching: 5 min TTL in-process (threading.Lock + monotonic timestamp).
Returns None when the mart view is absent or the query fails — callers must
handle None gracefully (degrade the UI strip without crashing).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

import duckdb

from app.domain.shared import DataQualitySummary

from .capability_adapter import DuckDbCapabilityAdapter
from .connection import SESSION_TIMEZONE

logger = logging.getLogger(__name__)

_DQ_CACHE_TTL_SECONDS: float = 300.0  # 5 min — aligns with schema cache TTL

_SELECT_MART = """
SELECT
    dq_key,
    as_of_utc,
    total_orders,
    cogs_rate_pct,
    platform_fees_rate_pct,
    fulfillment_coverage_pct,
    return_rate_pct,
    us_share_pct,
    carrier_null_rate_pct,
    acq_source_null_rate_pct
FROM mart_data_quality
LIMIT 1
"""


class DuckDbDataQualityAdapter:
    """Implements DataQualityPort. Thread-safe, in-process TTL cache."""

    def __init__(self, db_path: str, capability: DuckDbCapabilityAdapter) -> None:
        self._db_path = db_path
        self._cap = capability
        self._lock = threading.Lock()
        self._cache: DataQualitySummary | None = None
        self._cache_ts: float = 0.0

    # ------------------------------------------------------------------
    # DataQualityPort interface
    # ------------------------------------------------------------------

    def coverage_metrics(self) -> DataQualitySummary | None:
        """Return system-wide coverage snapshot, or None when mart is unavailable.

        Result is cached for _DQ_CACHE_TTL_SECONDS. The cache stores None when
        the mart view is absent so we don't hammer the DB on repeated calls.
        """
        now = time.monotonic()
        with self._lock:
            if self._cache_ts > 0 and (now - self._cache_ts) <= _DQ_CACHE_TTL_SECONDS:
                return self._cache
            result = self._fetch()
            self._cache = result
            self._cache_ts = now
            return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self) -> DataQualitySummary | None:
        """Query mart_data_quality and compose DataQualitySummary. Returns None on failure."""
        # Guard: skip DB round-trip if the view doesn't exist yet.
        if not self._cap.view_exists("mart_data_quality"):
            logger.info("DataQualityAdapter: mart_data_quality view absent — returning None")
            return None

        row: dict | None = None
        try:
            with duckdb.connect(self._db_path, read_only=True) as conn:
                conn.execute(f"SET TimeZone='{SESSION_TIMEZONE}'")
                cursor = conn.execute(_SELECT_MART)
                raw = cursor.fetchone()
                if raw is not None:
                    cols = [c[0] for c in (cursor.description or [])]
                    row = dict(zip(cols, raw))
        except Exception:  # noqa: BLE001
            logger.warning("DataQualityAdapter: mart_data_quality query failed", exc_info=True)
            return None

        if row is None:
            # View exists but has no rows (shouldn't happen for a 1-row mart).
            logger.info("DataQualityAdapter: mart_data_quality is empty")
            return None

        # Resolve as_of_utc to a timezone-aware datetime.
        as_of = _coerce_dt(row.get("as_of_utc"))

        # Derive capability signals (schema-level booleans).
        has_carrier_link = (
            self._cap.has_column("fact_fulfillments", "carrier_url")
            or self._cap.view_exists("dim_carriers")
        )
        stale = self._cap.stale_views(threshold_hours=48.0)
        version = self._cap.data_version()

        return DataQualitySummary(
            data_version=version,
            as_of=as_of,
            total_orders=_coerce_int(row.get("total_orders")),
            cogs_rate_pct=_coerce_float(row.get("cogs_rate_pct")),
            platform_fees_rate_pct=_coerce_float(row.get("platform_fees_rate_pct")),
            fulfillment_coverage_pct=_coerce_float(row.get("fulfillment_coverage_pct")),
            return_rate_pct=_coerce_float(row.get("return_rate_pct")),
            us_share_pct=_coerce_float(row.get("us_share_pct")),
            carrier_null_rate_pct=_coerce_float(row.get("carrier_null_rate_pct")),
            acq_source_null_rate_pct=_coerce_float(row.get("acq_source_null_rate_pct")),
            stale_views=stale,
            has_carrier_link_map=has_carrier_link,
        )


# ------------------------------------------------------------------
# Type coercions (defensive — mart schema may drift)
# ------------------------------------------------------------------

def _coerce_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _coerce_int(val: object) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _coerce_dt(val: object) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        # Ensure timezone-aware (mart stores TIMESTAMPTZ → DuckDB returns tz-aware).
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    try:
        # Fallback for string representations.
        return datetime.fromisoformat(str(val))
    except (TypeError, ValueError):
        return None
