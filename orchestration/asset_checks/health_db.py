"""Read-only SQLite helpers for ingestion_health.db.

All functions accept an open connection and return plain Python values.
Callers are responsible for opening/closing via open_readonly().
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Generator, Optional

from orchestration.ops.ingestion_health import get_db_path
import orchestration.ops.ingestion_health  # noqa: F401 — registers sqlite3 adapters/converters


@contextmanager
def open_readonly() -> Generator[sqlite3.Connection, None, None]:
    """Context manager: open ingestion_health.db for reading (query_only)."""
    conn = sqlite3.connect(get_db_path(), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA query_only=ON")
    try:
        yield conn
    finally:
        conn.close()


def last_success(conn: sqlite3.Connection, asset_key: str) -> Optional[datetime]:
    """Return run_started_at of the most recent successful run, or None."""
    row = conn.execute(
        """
        SELECT run_started_at
        FROM ingestion_runs
        WHERE asset_key = ? AND status = 'success'
        ORDER BY run_started_at DESC
        LIMIT 1
        """,
        [asset_key],
    ).fetchone()
    return row[0] if row else None


def rows_by_day(
    conn: sqlite3.Connection,
    asset_key: str,
    n_days: int = 8,
) -> list[tuple[date, int]]:
    """Return (day, total_rows_written) for the last n_days of successful runs."""
    rows = conn.execute(
        """
        SELECT
            date(run_started_at) AS d,
            SUM(COALESCE(rows_written, 0)) AS r
        FROM ingestion_runs
        WHERE asset_key = ? AND status = 'success'
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT ?
        """,
        [asset_key, n_days],
    ).fetchall()
    return [(date.fromisoformat(row[0]), int(row[1])) for row in rows]


def consecutive_empty_with_cursor_move(
    conn: sqlite3.Connection,
    asset_key: str,
    streak_n: int = 3,
) -> int:
    """Return the count of the most recent streak of runs where cursor advanced but rows_written=0.

    Returns 0 if cursor columns are null or no streak detected.
    Streak is broken as soon as a run has rows_written > 0 or cursor didn't move.
    """
    rows = conn.execute(
        """
        SELECT cursor_before, cursor_after, COALESCE(rows_written, 0) AS rows_written
        FROM ingestion_runs
        WHERE asset_key = ? AND status = 'success'
          AND cursor_before IS NOT NULL AND cursor_after IS NOT NULL
        ORDER BY run_started_at DESC
        LIMIT ?
        """,
        [asset_key, streak_n],
    ).fetchall()

    if not rows:
        return 0

    streak = 0
    for cursor_before, cursor_after, rows_written in rows:
        if cursor_before != cursor_after and rows_written == 0:
            streak += 1
        else:
            break

    return streak


def count_zero_row_runs_last_24h(
    conn: sqlite3.Connection,
    asset_key: str,
) -> tuple[int, int]:
    """Return (total_runs_last_24h, zero_row_runs_last_24h)."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE COALESCE(rows_written, 0) = 0) AS zero_rows
        FROM ingestion_runs
        WHERE asset_key = ?
          AND run_started_at >= datetime('now', '-24 hours')
          AND status = 'success'
        """,
        [asset_key],
    ).fetchone()
    if row is None:
        return 0, 0
    return int(row[0]), int(row[1])
