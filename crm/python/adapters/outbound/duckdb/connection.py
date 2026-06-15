"""Read-only DuckDB connection helper for CRM order detail queries.

Opens olap.duckdb in read_only=True so it runs safely alongside Metabase and the
dbt/Dagster writer. The file may not exist at startup (non-fatal for CRM — the
server will return 503 for order detail endpoints until the serving layer is ready).

Connection lifecycle is *per request*: open -> use -> close via open_olap().
"""
from __future__ import annotations

import logging
import time

import duckdb

logger = logging.getLogger(__name__)

# Serving layer displays TIMESTAMPTZ in ICT (pipeline stores UTC-native TIMESTAMPTZ).
SESSION_TIMEZONE = "Asia/Ho_Chi_Minh"

# Retry policy for the transient RW lock held during serving-view bootstrap.
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.2


def open_olap(path: str) -> duckdb.DuckDBPyConnection | None:
    """Open olap.duckdb read-only with ICT session timezone.

    Retries up to _MAX_ATTEMPTS times with linear backoff on IOException
    (transient write lock during bootstrap_serving_views.py window).

    Returns None on any error so callers can degrade gracefully — olap.duckdb
    may not exist yet, which is non-fatal for CRM (server returns 503 instead).

    Args:
        path: Absolute path to olap.duckdb. Driven by env var at composition root.

    Returns:
        Open read-only DuckDBPyConnection, or None if unavailable.
    """
    last_err: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            conn = duckdb.connect(path, read_only=True)
            conn.execute(f"SET TimeZone='{SESSION_TIMEZONE}'")
            return conn
        except duckdb.IOException as err:
            last_err = err
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_BACKOFF_SECONDS * (attempt + 1))
        except Exception as err:  # noqa: BLE001 — missing file, corrupt DB, etc.
            last_err = err
            break

    logger.warning("crm duckdb: could not open %r — order detail unavailable: %s", path, last_err)
    return None
