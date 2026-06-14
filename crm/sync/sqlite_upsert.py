"""
sqlite_upsert.py — idempotent SQLite upsert helpers for cache.db.

Opens cache.db with WAL + busy_timeout pragmas.
Applies cache_schema.sql (CREATE TABLE IF NOT EXISTS — safe to call repeatedly).
Exposes typed upsert functions that use INSERT … ON CONFLICT(pk) DO UPDATE
with executemany batching for throughput.

Python is the SOLE writer of cache.db; Go ATTACHes it read-only.
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any


_SCHEMA_SQL = pathlib.Path(__file__).with_name("cache_schema.sql").read_text(encoding="utf-8")


def open_cache_db(path: str) -> sqlite3.Connection:
    """
    Open cache.db with WAL mode, busy_timeout, and NORMAL synchronous.

    Returns an open connection; caller is responsible for closing it.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    # No FK enforcement in cache.db: bulk-load order is not guaranteed.
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply cache_schema.sql (CREATE TABLE / INDEX IF NOT EXISTS — idempotent)."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


# ─── Upsert helpers ──────────────────────────────────────────────────────────

def _upsert(
    conn: sqlite3.Connection,
    table: str,
    pk: str,
    rows: list[dict[str, Any]],
) -> int:
    """
    Generic INSERT … ON CONFLICT DO UPDATE upsert via executemany.

    All columns from the first row are used (must be consistent across rows).
    Returns number of rows processed.
    """
    if not rows:
        return 0

    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    update_set = ", ".join(
        f"{c} = excluded.{c}" for c in cols if c != pk
    )

    sql = (
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT({pk}) DO UPDATE SET {update_set}"
    )

    values = [tuple(row.get(c) for c in cols) for row in rows]
    with conn:
        conn.executemany(sql, values)
    return len(rows)


def upsert_customer_insight(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_customer_insight", "customer_key", rows)


def upsert_product_insight(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_product_insight", "product_key", rows)


def upsert_action_queue(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_action_queue", "action_id", rows)


def upsert_customer_base(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_customer_base", "customer_key", rows)


def upsert_product(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_product", "product_key", rows)


def upsert_order_hdr(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_order_hdr", "order_id", rows)


def upsert_party_seed(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """
    Upsert rows into wh_party_seed.
    Each row: {customer_id, customer_key, seen_at}.
    seen_at is only updated if not already present (keep first-seen timestamp).
    """
    if not rows:
        return 0
    sql = (
        "INSERT INTO wh_party_seed (customer_id, customer_key, seen_at) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(customer_id) DO UPDATE SET customer_key = excluded.customer_key"
        # seen_at intentionally not updated: preserve first-seen timestamp
    )
    values = [(r["customer_id"], r["customer_key"], r["seen_at"]) for r in rows]
    with conn:
        conn.executemany(sql, values)
    return len(rows)


def insert_sync_run(conn: sqlite3.Connection, row: dict) -> None:
    """Insert a single wh_sync_run audit row."""
    sql = (
        "INSERT INTO wh_sync_run "
        "(run_id, source_table, row_count, status, started_at, finished_at, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    with conn:
        conn.execute(sql, (
            row["run_id"],
            row["source_table"],
            row.get("row_count"),
            row.get("status"),
            row.get("started_at"),
            row.get("finished_at"),
            row.get("error"),
        ))


def get_max_order_date_key(conn: sqlite3.Connection) -> int | None:
    """Return the maximum date_key already stored in wh_order_hdr, or None if empty."""
    row = conn.execute("SELECT MAX(date_key) FROM wh_order_hdr").fetchone()
    if row and row[0] is not None:
        return int(row[0])
    return None
