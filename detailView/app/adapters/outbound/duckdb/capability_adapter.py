"""DuckDB implementation of CapabilityPort.

Provides schema introspection and filesystem freshness signals:
- view_exists / has_column: query information_schema.columns, cached 5 min.
- data_version: lexically-max parquet basename across rolling dirs, cached 60 s.
- freshness: latest parquet mtime per view dir (always-fresh filesystem stat).
- known_tables: read .known_tables.json (lock-free JSON read, always-fresh).

Cache is in-process (threading.Lock + monotonic timestamp). Safe for single-worker
FastAPI. For multi-worker deployments each worker converges independently after TTL.
"""
from __future__ import annotations

import glob as _glob
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any

import duckdb

from .connection import SESSION_TIMEZONE

logger = logging.getLogger(__name__)

# Schema changes are rare (require manual bootstrap_serving_views.py run).
_SCHEMA_CACHE_TTL_SECONDS: float = 300.0  # 5 min
# data_version refreshes per pipeline run (~daily); 60 s is fine.
_VERSION_CACHE_TTL_SECONDS: float = 60.0


class DuckDbCapabilityAdapter:
    """Implements CapabilityPort. Thread-safe, in-process TTL cache."""

    def __init__(self, db_path: str, rolling_dir: str, known_tables_path: str) -> None:
        self._db_path = db_path
        self._rolling_dir = rolling_dir
        self._known_tables_path = known_tables_path
        self._lock = threading.Lock()

        self._schema_cache: dict[str, set[str]] | None = None
        self._schema_cache_ts: float = 0.0

        self._version_cache: str | None = None
        self._version_cache_ts: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_schema(self) -> dict[str, set[str]]:
        """Return {view_name: set(column_names)}. Cached for _SCHEMA_CACHE_TTL_SECONDS."""
        now = time.monotonic()
        with self._lock:
            if self._schema_cache is None or (now - self._schema_cache_ts) > _SCHEMA_CACHE_TTL_SECONDS:
                self._schema_cache = self._fetch_schema()
                self._schema_cache_ts = now
            return self._schema_cache

    def _fetch_schema(self) -> dict[str, set[str]]:
        """Hit information_schema.columns once; build view→columns mapping."""
        schema: dict[str, set[str]] = {}
        try:
            with duckdb.connect(self._db_path, read_only=True) as conn:
                conn.execute(f"SET TimeZone='{SESSION_TIMEZONE}'")
                rows = conn.execute(
                    "SELECT table_name, column_name FROM information_schema.columns"
                ).fetchall()
            for table, col in rows:
                schema.setdefault(table, set()).add(col)
        except Exception:  # noqa: BLE001 — degrade gracefully on any DB error
            logger.warning("CapabilityAdapter: schema fetch failed; returning empty schema", exc_info=True)
        return schema

    # ------------------------------------------------------------------
    # CapabilityPort interface
    # ------------------------------------------------------------------

    def view_exists(self, view_name: str) -> bool:
        """True if view_name is present in information_schema."""
        return view_name in self._load_schema()

    def has_column(self, view_name: str, column_name: str) -> bool:
        """True if view_name has a column named column_name."""
        schema = self._load_schema()
        return column_name in schema.get(view_name, set())

    def data_version(self) -> str:
        """Lexically-max parquet basename across all non-empty rolling dirs.

        Returns 'unknown' when rolling_dir is absent or has no parquet files.
        Cached for _VERSION_CACHE_TTL_SECONDS.
        """
        now = time.monotonic()
        with self._lock:
            if self._version_cache is None or (now - self._version_cache_ts) > _VERSION_CACHE_TTL_SECONDS:
                self._version_cache = _scan_max_filename(self._rolling_dir) or "unknown"
                self._version_cache_ts = now
            return self._version_cache

    def freshness(self, view_name: str) -> datetime | None:
        """Return the mtime of the latest parquet in view_name's rolling dir, or None."""
        table_dir = os.path.join(self._rolling_dir, view_name)
        if not os.path.isdir(table_dir):
            return None
        files = sorted(_glob.glob(os.path.join(table_dir, "*.parquet")))
        if not files:
            return None
        return datetime.fromtimestamp(os.path.getmtime(files[-1]))

    def known_tables(self) -> frozenset[str]:
        """Tables listed in .known_tables.json. Lock-free; always-fresh read."""
        try:
            with open(self._known_tables_path, encoding="utf-8") as fh:
                data: Any = json.load(fh)
            return frozenset(data.get("tables", []))
        except (OSError, ValueError):
            return frozenset()

    def stale_views(self, threshold_hours: float = 48.0) -> list[str]:
        """Return view names whose latest parquet mtime is older than threshold_hours.

        Used by DataQualitySummary.stale_views. Only considers dirs that exist;
        missing dirs (view never built) are not included.
        """
        stale: list[str] = []
        if not os.path.isdir(self._rolling_dir):
            return stale
        cutoff = time.time() - threshold_hours * 3600
        for entry in os.listdir(self._rolling_dir):
            table_dir = os.path.join(self._rolling_dir, entry)
            if not os.path.isdir(table_dir):
                continue
            files = sorted(_glob.glob(os.path.join(table_dir, "*.parquet")))
            if not files:
                continue
            mtime = os.path.getmtime(files[-1])
            if mtime < cutoff:
                stale.append(entry)
        return sorted(stale)


# ------------------------------------------------------------------
# Module-level helper (no instance state needed)
# ------------------------------------------------------------------

def _scan_max_filename(rolling_dir: str) -> str | None:
    """Return the lexically-maximum parquet basename across all table subdirs."""
    if not os.path.isdir(rolling_dir):
        return None
    max_fn: str | None = None
    for entry in os.listdir(rolling_dir):
        table_dir = os.path.join(rolling_dir, entry)
        if not os.path.isdir(table_dir):
            continue
        files = sorted(_glob.glob(os.path.join(table_dir, "*.parquet")))
        if files:
            fn = os.path.basename(files[-1])
            if max_fn is None or fn > max_fn:
                max_fn = fn
    return max_fn
