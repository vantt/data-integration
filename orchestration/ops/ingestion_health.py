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
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import duckdb

# --- Path resolution ---
# Priority: explicit env var > DAGSTER_HOME-derived > module-relative fallback.
# Module fallback: this file lives at <project_root>/orchestration/ops/ingestion_health.py,
# so project_root = parents[2]. This works for local dev regardless of CWD.
def _resolve_db_path() -> str:
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit

    # Candidate 1: DAGSTER_HOME (production Dagster deployment)
    dagster_home = os.environ.get("DAGSTER_HOME")
    if dagster_home:
        candidate = Path(dagster_home).parent / "app_data" / "data_lake" / "monitoring" / "ingestion_health.duckdb"
        if candidate.parent.parent.exists():  # app_data/data_lake exists
            return str(candidate)

    # Candidate 2: Docker fixed path
    docker_path = Path("/app/app_data/data_lake/monitoring/ingestion_health.duckdb")
    if docker_path.parent.parent.exists():
        return str(docker_path)

    # Candidate 3: module-relative (local dev, any CWD)
    project_root = Path(__file__).resolve().parents[2]
    return str(project_root / "app_data" / "data_lake" / "monitoring" / "ingestion_health.duckdb")


_HEALTH_DB_PATH = _resolve_db_path()


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


def _connect() -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(_HEALTH_DB_PATH), exist_ok=True)
    conn = duckdb.connect(_HEALTH_DB_PATH)
    conn.execute(_DDL)
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
                json.dumps(metadata) if metadata else None,
            ],
        )


def get_db_path() -> str:
    """Return the resolved DuckDB path (for diagnostics / tooling)."""
    return _HEALTH_DB_PATH
