"""Ingestion-health recorder.

Persists one row per ingestion asset run into a dedicated SQLite instance
(`/app/var/data_lake/monitoring/ingestion_health.db` inside Docker) independent of
Dagster's event log (which is short-lived) and of the serving DB.

Public API:
    record_run(asset_key, run_id, run_started_at, ..., metadata=None)

Design:
- WAL mode: supports concurrent reads + writes — no single-writer limitation.
- Lazy-init: CREATE TABLE IF NOT EXISTS on first write.
- PK = (asset_key, run_id) — idempotent retries.
- `metadata_json` is the escape hatch for source-specific fields.
- Datetimes stored as UTC ISO8601 TEXT (space separator, SQLite-compatible).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class _DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects from DLT/pendulum."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "total_seconds"):
            return obj.total_seconds()
        return super().default(obj)


logger = logging.getLogger(__name__)


def _resolve_db_path() -> str:
    """Resolve SQLite file path from environment — no hardcoded paths.

    Priority:
    1. INGESTION_HEALTH_DB        — full file path override.
    2. DBT_DATA_LAKE_PATH         — data_lake root; appends /monitoring/ingestion_health.db.
    """
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit

    data_lake = os.environ.get("DBT_DATA_LAKE_PATH")
    if data_lake:
        return str(Path(data_lake) / "monitoring" / "ingestion_health.db")

    raise RuntimeError(
        "ingestion_health: cannot resolve DB path — set INGESTION_HEALTH_DB or "
        "DBT_DATA_LAKE_PATH (e.g. via .env.local for host runs, .env.docker for "
        "containers). Refusing to write to a hardcoded fallback."
    )


# --- SQLite datetime adapters ---
# Store as UTC ISO8601 with space separator (SQLite datetime() functions use this format).

def _adapt_datetime(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def _convert_datetime(b: bytes) -> Optional[datetime]:
    s = b.decode()
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMPTZ", _convert_datetime)


_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       TEXT NOT NULL,
    run_id          TEXT NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    duration_s      REAL,
    status          TEXT NOT NULL,
    rows_fetched    INTEGER,
    rows_written    INTEGER,
    rows_new        INTEGER,
    rows_updated    INTEGER,
    cursor_before   TEXT,
    cursor_after    TEXT,
    schema_hash     TEXT,
    file_sha256     TEXT,
    file_mtime      TIMESTAMPTZ,
    metadata_json   TEXT,
    PRIMARY KEY (asset_key, run_id)
);
"""


def _connect() -> sqlite3.Connection:
    path = _resolve_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(_DDL)
    conn.commit()
    return conn


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
    the underlying asset materialization.
    """
    ended = run_ended_at or datetime.now(timezone.utc)
    duration_s = (ended - run_started_at).total_seconds() if run_started_at else None

    conn = _connect()
    try:
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
        conn.commit()
    finally:
        conn.close()


def get_db_path() -> str:
    """Return the resolved DB path (for diagnostics / tooling)."""
    return _resolve_db_path()


def check_writable() -> tuple[bool, str]:
    """Try to open the health DB in write mode.

    Returns (ok, error_message). Used by the watchdog sensor.
    """
    conn = None
    try:
        path = _resolve_db_path()
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
        return True, ""
    except Exception as exc:
        return False, str(exc)[:300]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
