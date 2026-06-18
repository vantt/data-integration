"""DuckDB read-only repository for mart_data_quality — data-health footer strip.

Degrades gracefully when mart_data_quality view is absent or olap.duckdb is
unavailable — returns None rather than raising so the strip simply stays empty.
5-minute in-memory cache avoids repeated DuckDB opens per page load.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import duckdb

from domain.entities.data_quality import DataQualitySummary

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 minutes

_SQL_VIEW_EXISTS = """
    SELECT count(*) FROM information_schema.views
    WHERE table_name = 'mart_data_quality'
"""

_SQL_FETCH = "SELECT as_of_ict, cogs_rate_pct FROM mart_data_quality LIMIT 1"


class DataQualityRepository:
    """Read-only access to mart_data_quality with TTL caching."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._cache: Optional[DataQualitySummary] = None
        self._cache_ts: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> Optional[DataQualitySummary]:
        """Return DataQualitySummary or None (on error / missing view).

        Cached for _CACHE_TTL_SECONDS to avoid hammering DuckDB on every page load.
        """
        with self._lock:
            if self._cache is not None and (time.monotonic() - self._cache_ts) < _CACHE_TTL_SECONDS:
                return self._cache

        result = self._fetch()

        with self._lock:
            self._cache = result
            self._cache_ts = time.monotonic()

        return result

    # ── private ───────────────────────────────────────────────────────────────

    def _fetch(self) -> Optional[DataQualitySummary]:
        try:
            with duckdb.connect(self._db_path, read_only=True) as conn:
                conn.execute("SET TimeZone='Asia/Ho_Chi_Minh'")

                # Guard: skip if view doesn't exist yet.
                count_row = conn.execute(_SQL_VIEW_EXISTS).fetchone()
                if not count_row or count_row[0] == 0:
                    return None

                row = conn.execute(_SQL_FETCH).fetchone()
                if row is None:
                    return None

                as_of_ict, cogs_rate_pct = row
                as_of_str = as_of_ict.strftime("%Y-%m-%d %H:%M") if as_of_ict else ""

                return DataQualitySummary(
                    as_of_str=as_of_str,
                    cogs_rate_pct=float(cogs_rate_pct) if cogs_rate_pct is not None else None,
                    stale_views=[],
                )
        except Exception:  # noqa: BLE001 — missing file, corrupt DB, lock, etc.
            logger.warning("dataquality_repository: fetch failed", exc_info=True)
            return None
