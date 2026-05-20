"""Ingestion-health recorder.

Persists one row per ingestion asset run into a dedicated DuckDB instance
(`app_data/data_lake/monitoring/ingestion_health.duckdb`) independent of
Dagster's event log (which is short-lived) and of the serving DB (to avoid
lock contention with Metabase).

Public API:
    record_run(asset_key, run_id, run_started_at, ..., metadata=None)

Design:
- Lazy-init: CREATE TABLE IF NOT EXISTS on first write.
- PK = (asset_key, run_id) — idempotent retries.
- `metadata_json` is the escape hatch for source-specific fields.
- Derived metrics (expected_rows, drift vs median, etc.) are computed at
  query time via window functions — nothing derived is persisted.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import duckdb


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects from DLT/pendulum."""

    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle pendulum DateTime (has isoformat)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        # Handle pendulum Duration/Interval
        if hasattr(obj, "total_seconds"):
            return obj.total_seconds()
        return super().default(obj)

logger = logging.getLogger(__name__)

# --- Path resolution ---
# Priority: explicit env var > DAGSTER_HOME-derived > module-relative fallback.
# Module fallback: this file lives at <project_root>/orchestration/ops/ingestion_health.py,
# so project_root = parents[2]. This works for local dev regardless of CWD.
def _resolve_db_path() -> str:
    """Resolve DuckDB file path from environment — no hardcoded paths.

    Priority:
    1. INGESTION_HEALTH_DB        — full file path override.
    2. DBT_DATA_LAKE_PATH         — data_lake root; appends /monitoring/ingestion_health.duckdb.
                                    Already defined in .env.{docker,local,example}.

    Raises RuntimeError if neither is set — fail loud, do NOT fall back to a
    hardcoded path that could be ephemeral or wrong for the deployment.
    """
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit

    data_lake = os.environ.get("DBT_DATA_LAKE_PATH")
    if data_lake:
        return str(Path(data_lake) / "monitoring" / "ingestion_health.duckdb")

    raise RuntimeError(
        "ingestion_health: cannot resolve DB path — set INGESTION_HEALTH_DB or "
        "DBT_DATA_LAKE_PATH (e.g. via .env.local for host runs, .env.docker for "
        "containers). Refusing to write to a hardcoded fallback."
    )


# Path resolved lazily inside _connect()/get_db_path() so import never fails
# when env is missing — only actual writes do.


_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       VARCHAR NOT NULL,
    run_id          VARCHAR NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    duration_s      DOUBLE,
    status          VARCHAR NOT NULL,           -- success | partial | failed | skipped
    rows_fetched    BIGINT,                     -- from source (nullable if source can't report)
    rows_written    BIGINT,                     -- into destination
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


_LOCK_RETRIES = 8
_LOCK_BACKOFF_S = 1.0

# Hint shown when a Windows shell/Defender process holds the lock.
_LOCK_HINT = (
    "Fix: Add Windows Defender exclusion for the monitoring directory, or run "
    "'taskkill /F /IM dllhost.exe' on the Windows host to release COM surrogate lock. "
    "See health_db_watchdog_sensor for automated detection."
)


def _connect() -> duckdb.DuckDBPyConnection:
    path = _resolve_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(_LOCK_RETRIES):
        try:
            conn = duckdb.connect(path)
            conn.execute(_DDL)
            return conn
        except duckdb.IOException as exc:
            last_err = exc
            err_str = str(exc)
            is_stale = "PID 0" in err_str or "being used by another process" in err_str
            if attempt < _LOCK_RETRIES - 1:
                wait = _LOCK_BACKOFF_S * (2 ** attempt)
                if is_stale and attempt == 0:
                    logger.warning(
                        "ingestion_health: stale lock on %s (attempt %d/%d) — %s",
                        path, attempt + 1, _LOCK_RETRIES, _LOCK_HINT,
                    )
                else:
                    logger.warning(
                        "ingestion_health lock contention (attempt %d/%d), retry in %.1fs",
                        attempt + 1, _LOCK_RETRIES, wait,
                    )
                time.sleep(wait)
    raise last_err  # type: ignore[misc]


def record_run(
    asset_key: str,
    run_id: str,
    run_started_at: datetime,
    run_ended_at: Optional[datetime] = None,
    status: str = "success",
    rows_fetched: Optional[int] = None,
    rows_written: Optional[int] = None,
    rows_new: Optional[int] = None,
    rows_updated: Optional[int] = None,
    cursor_before: Optional[str] = None,
    cursor_after: Optional[str] = None,
    schema_hash: Optional[str] = None,
    file_sha256: Optional[str] = None,
    file_mtime: Optional[datetime] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Idempotent INSERT OR REPLACE of a single ingestion run record.

    Callers should be best-effort: a failure to record health MUST NOT fail
    the underlying asset materialization. The Dagster asset wrapper is
    expected to catch any exception from this function.
    """
    ended = run_ended_at or datetime.now(timezone.utc)
    duration_s = (ended - run_started_at).total_seconds() if run_started_at else None

    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO ingestion_runs (
                asset_key, run_id, run_started_at, run_ended_at, duration_s, status,
                rows_fetched, rows_written, rows_new, rows_updated,
                cursor_before, cursor_after,
                schema_hash, file_sha256, file_mtime,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                asset_key,
                run_id,
                run_started_at,
                ended,
                duration_s,
                status,
                rows_fetched,
                rows_written,
                rows_new,
                rows_updated,
                cursor_before,
                cursor_after,
                schema_hash,
                file_sha256,
                file_mtime,
                json.dumps(metadata, cls=_DateTimeEncoder) if metadata else None,
            ],
        )


def get_db_path() -> str:
    """Return the resolved DuckDB path (for diagnostics / tooling)."""
    return _resolve_db_path()


def check_writable() -> tuple[bool, str]:
    """Try to open the health DB in write mode (no retries, no DDL).

    Returns (ok, error_message). Used by the watchdog sensor to distinguish
    a ghost lock from a recorder code bug.
    """
    conn = None
    try:
        path = _resolve_db_path()
        conn = duckdb.connect(path)
        return True, ""
    except Exception as exc:
        return False, str(exc)[:300]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
