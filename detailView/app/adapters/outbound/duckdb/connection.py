"""Read-only DuckDB connection helper for the outbound adapter.

Opens the serving OLAP database in ``read_only=True`` mode so it can run safely
alongside Metabase and the dbt/Dagster writer. The serving views are bootstrapped
by another process; during that brief window the file may hold a short-lived
read/write lock, so we retry a few times on ``IOException`` before giving up.

Connection lifecycle is *per request*: open -> use -> close. Callers should use the
``read_only_connection`` context manager rather than holding a long-lived handle.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

import duckdb

# Session timezone — all TIMESTAMPTZ columns must surface in ICT (Asia/Ho_Chi_Minh).
# The pipeline stores UTC-native TIMESTAMPTZ; the serving layer displays ICT.
SESSION_TIMEZONE = "Asia/Ho_Chi_Minh"

# Retry policy for the transient RW lock held during serving-view bootstrap.
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.2


def read_only_connect(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open a read-only DuckDB connection with the ICT session timezone set.

    Retries up to ``_MAX_ATTEMPTS`` times with linear backoff when the file is
    briefly locked (``duckdb.IOException``) by the view-bootstrap writer.

    Args:
        db_path: Absolute path to the serving ``olap.duckdb`` file. Driven by the
            ``OLAP_DB_PATH`` env var at the composition root — never hardcode.

    Returns:
        An open, read-only ``DuckDBPyConnection``. Caller owns closing it.

    Raises:
        duckdb.IOException: If the database is still locked after all retries.
    """
    last_error: duckdb.IOException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            connection = duckdb.connect(db_path, read_only=True)
            # SET TimeZone affects strftime/casts on TIMESTAMPTZ columns.
            connection.execute(f"SET TimeZone='{SESSION_TIMEZONE}'")
            return connection
        except duckdb.IOException as error:
            last_error = error
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_BACKOFF_SECONDS * (attempt + 1))
    # Exhausted retries — surface the original lock error to the caller.
    assert last_error is not None  # loop always assigns on the IOException path
    raise last_error


@contextmanager
def read_only_connection(db_path: str) -> Iterator[duckdb.DuckDBPyConnection]:
    """Per-request connection context manager: open -> yield -> always close."""
    connection = read_only_connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
