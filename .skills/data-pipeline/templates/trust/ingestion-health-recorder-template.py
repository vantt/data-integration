"""Ingestion health recorder — reusable template.

Drop into ``orchestration/ops/ingestion_health.py`` (or equivalent) and customize
the env-var names. Public API: ``record_run(asset_key, run_id, ...)``.

Design invariants:
  1. PK = (asset_key, run_id). Dagster/Airflow share run_id across sibling
     assets in the same job — DML that filters only on run_id corrupts siblings.
  2. Lazy DDL (CREATE TABLE IF NOT EXISTS on first write). Import never fails.
  3. Path resolution fails loud when env is unset — do NOT fall back to a
     hardcoded path that diverges between host and container.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import duckdb

logger = logging.getLogger(__name__)


class _DateTimeEncoder(json.JSONEncoder):
    """Handles datetime / pendulum / timedelta-like objects in LoadInfo dicts."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "total_seconds"):
            return obj.total_seconds()
        return super().default(obj)


_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       VARCHAR NOT NULL,
    run_id          VARCHAR NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    duration_s      DOUBLE,
    status          VARCHAR NOT NULL,           -- success | skipped | failed | partial
    rows_fetched    BIGINT,                     -- from source
    rows_written    BIGINT,                     -- to destination
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


def get_db_path() -> str:
    """Resolve DuckDB file path from env. Fail loud when unset.

    Priority:
      1. INGESTION_HEALTH_DB  — explicit full-path override
      2. DBT_DATA_LAKE_PATH   — root; appends /monitoring/ingestion_health.duckdb
    """
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit
    data_lake = os.environ.get("DBT_DATA_LAKE_PATH")
    if data_lake:
        return str(Path(data_lake) / "monitoring" / "ingestion_health.duckdb")
    raise RuntimeError(
        "ingestion_health: cannot resolve DB path — set INGESTION_HEALTH_DB or "
        "DBT_DATA_LAKE_PATH. Refusing hardcoded fallback."
    )


def _connect() -> duckdb.DuckDBPyConnection:
    path = get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(path)
    conn.execute(_DDL)
    return conn


def record_run(
    *,
    asset_key: str,
    run_id: str,
    run_started_at: datetime,
    status: str,
    run_ended_at: Optional[datetime] = None,
    rows_fetched: Optional[int] = None,
    rows_written: Optional[int] = None,
    rows_new: Optional[int] = None,
    rows_updated: Optional[int] = None,
    cursor_before: Optional[str] = None,
    cursor_after: Optional[str] = None,
    schema_hash: Optional[str] = None,
    file_sha256: Optional[str] = None,
    file_mtime: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Persist one ingestion run. Idempotent via UPSERT on (asset_key, run_id).

    MUST be wrapped in try/except at call sites — this function can raise if
    the health DB is momentarily locked. Health is observability, not a
    blocker on ingestion success.
    """
    if run_ended_at is None:
        run_ended_at = datetime.now(timezone.utc)
    duration_s = (run_ended_at - run_started_at).total_seconds()

    meta_json: Optional[str] = None
    if metadata is not None:
        try:
            meta_json = json.dumps(metadata, cls=_DateTimeEncoder)
        except Exception as exc:
            logger.warning("ingestion_health: metadata json encode failed: %s", exc)
            meta_json = None

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO ingestion_runs
                (asset_key, run_id, run_started_at, run_ended_at, duration_s,
                 status, rows_fetched, rows_written, rows_new, rows_updated,
                 cursor_before, cursor_after, schema_hash, file_sha256,
                 file_mtime, metadata_json)
            VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?, ?, ?)
            ON CONFLICT (asset_key, run_id) DO UPDATE SET
                run_ended_at = EXCLUDED.run_ended_at,
                duration_s   = EXCLUDED.duration_s,
                status       = EXCLUDED.status,
                rows_fetched = EXCLUDED.rows_fetched,
                rows_written = EXCLUDED.rows_written,
                rows_new     = EXCLUDED.rows_new,
                rows_updated = EXCLUDED.rows_updated,
                cursor_before= EXCLUDED.cursor_before,
                cursor_after = EXCLUDED.cursor_after,
                schema_hash  = EXCLUDED.schema_hash,
                file_sha256  = EXCLUDED.file_sha256,
                file_mtime   = EXCLUDED.file_mtime,
                metadata_json= EXCLUDED.metadata_json
            """,
            [
                asset_key, run_id, run_started_at, run_ended_at, duration_s,
                status, rows_fetched, rows_written, rows_new, rows_updated,
                cursor_before, cursor_after, schema_hash, file_sha256,
                file_mtime, meta_json,
            ],
        )
    finally:
        conn.close()


def consecutive_empty_with_cursor_move(
    conn: duckdb.DuckDBPyConnection,
    asset_key: str,
    streak_n: int = 5,
) -> int:
    """Count consecutive recent runs where cursor advanced but rows_written=0.

    Used by the digest to detect "source went quiet" — a cursor that keeps
    moving forward but returns nothing suggests upstream truncation or bug.
    """
    rows = conn.execute(
        """
        SELECT rows_written, cursor_before, cursor_after
        FROM ingestion_runs
        WHERE asset_key = ?
          AND status IN ('success', 'skipped')
        ORDER BY run_started_at DESC
        LIMIT ?
        """,
        [asset_key, streak_n],
    ).fetchall()
    streak = 0
    for rw, c_before, c_after in rows:
        moved = c_after is not None and c_after != c_before
        empty = (rw or 0) == 0
        if moved and empty:
            streak += 1
        else:
            break
    return streak
