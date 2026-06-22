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

# ALTER TABLE migrations for columns added after initial schema creation.
# SQLite has no ADD COLUMN IF NOT EXISTS; catch OperationalError and continue.
# Statements run in order; idempotent by design (ALTER raises on re-run → caught).
_COLUMN_MIGRATIONS = [
    "ALTER TABLE wh_party_seed ADD COLUMN source_contact_quality TEXT NOT NULL DEFAULT 'real'",
    "ALTER TABLE wh_party_seed ADD COLUMN contact_quality TEXT NOT NULL DEFAULT 'real'",
    "ALTER TABLE wh_customer_base ADD COLUMN source_contact_quality TEXT NOT NULL DEFAULT 'real'",
    "ALTER TABLE wh_customer_base ADD COLUMN contact_quality TEXT NOT NULL DEFAULT 'real'",
    # wh_action_queue episode-based dedup: keep only the latest row per (customer_key, action_type)
    # before adding the UNIQUE index (prevents index creation failure on existing dbs with duplicates).
    """DELETE FROM wh_action_queue WHERE action_id IN (
        SELECT a.action_id FROM wh_action_queue a
        WHERE EXISTS (
            SELECT 1 FROM wh_action_queue b
            WHERE b.customer_key = a.customer_key
              AND b.action_type  = a.action_type
              AND b.generated_date > a.generated_date
        )
    )""",
    "ALTER TABLE wh_action_queue ADD COLUMN pending_since TEXT",
    "UPDATE wh_action_queue SET pending_since = generated_date WHERE pending_since IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uidx_wh_action_queue_customer_type ON wh_action_queue (customer_key, action_type)",
]


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
    """Apply cache_schema.sql (CREATE TABLE / INDEX IF NOT EXISTS — idempotent).
    Also runs ALTER TABLE column migrations for existing databases."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    for stmt in _COLUMN_MIGRATIONS:
        try:
            conn.execute(stmt)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists


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
    """Upsert action queue with episode-based stable action_id.

    action_id = md5(customer_key|action_type|pending_since) — stable for the lifetime of the episode.
    Conflict key: (customer_key, action_type) — one active row per type per customer.
    On conflict: updates data fields only; preserves action_id and pending_since.
    Cleanup: deletes rows not in today's batch (warehouse signal gone).
    """
    import hashlib

    upsert_sql = (
        "INSERT INTO wh_action_queue "
        "  (action_id, customer_key, action_type, rationale_vi, value_at_stake_vnd, "
        "   priority, pending_since, generated_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(customer_key, action_type) DO UPDATE SET "
        "  generated_date     = excluded.generated_date, "
        "  rationale_vi       = excluded.rationale_vi, "
        "  value_at_stake_vnd = excluded.value_at_stake_vnd, "
        "  priority           = excluded.priority, "
        "  refreshed_at       = strftime('%Y-%m-%dT%H:%M:%fZ','now')"
        # action_id and pending_since intentionally preserved on conflict
    )

    def _action_id(customer_key: str, action_type: str, date: str) -> str:
        return hashlib.md5(f"{customer_key}|{action_type}|{date}".encode()).hexdigest()

    values = [
        (
            _action_id(r["customer_key"], r["action_type"], r["generated_date"]),
            r["customer_key"],
            r["action_type"],
            r.get("rationale_vi"),
            r.get("value_at_stake_vnd"),
            r.get("priority"),
            r["generated_date"],   # pending_since = generated_date on first insert
            r["generated_date"],
        )
        for r in rows
    ]

    with conn:
        conn.executemany(upsert_sql, values)

        # Remove rows whose warehouse signal disappeared (signal-based full replacement).
        if rows:
            placeholders = ",".join(["(?,?)"] * len(rows))
            flat_args = [v for r in rows for v in (r["customer_key"], r["action_type"])]
            conn.execute(
                f"DELETE FROM wh_action_queue "
                f"WHERE (customer_key, action_type) NOT IN ({placeholders})",
                flat_args,
            )
        else:
            conn.execute("DELETE FROM wh_action_queue")

    return len(rows)


def upsert_customer_tier(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Full-replace upsert for wh_customer_tier (1 row per customer, keyed on customer_key).

    Uses generic _upsert (INSERT … ON CONFLICT DO UPDATE SET all columns) —
    identical pattern to upsert_customer_insight.  The warehouse produces exactly
    one tier row per customer; no episode logic needed.
    """
    return _upsert(conn, "wh_customer_tier", "customer_key", rows)


def upsert_customer_base(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_customer_base", "customer_key", rows)


def upsert_product(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_product", "product_key", rows)


def upsert_order_hdr(conn: sqlite3.Connection, rows: list[dict]) -> int:
    return _upsert(conn, "wh_order_hdr", "order_id", rows)


def upsert_party_seed(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """
    Upsert rows into wh_party_seed.
    Each row: {customer_id, customer_key, seen_at, source_contact_quality, contact_quality}.

    Only customer_key is updated on conflict — seen_at and quality fields use
    first-write-wins semantics so re-syncs don't overwrite CRM-upgraded contact_quality.
    """
    if not rows:
        return 0
    sql = (
        "INSERT INTO wh_party_seed "
        "(customer_id, customer_key, seen_at, source_contact_quality, contact_quality) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(customer_id) DO UPDATE SET customer_key = excluded.customer_key"
        # seen_at / quality fields intentionally not updated: first-write wins.
        # source_contact_quality is immutable; contact_quality is upgraded in crm.db by staff.
    )
    values = [
        (r["customer_id"], r["customer_key"], r["seen_at"],
         r.get("source_contact_quality", "real"), r.get("contact_quality", "real"))
        for r in rows
    ]
    with conn:
        conn.executemany(sql, values)
    return len(rows)


def upsert_deadstock_target(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Upsert dead-stock target queue rows into wh_deadstock_target.

    Composite PK (product_key, customer_key) — grain matches mart_deadstock_target_queue.
    Full-replace semantics: all columns updated on conflict (queue refreshes daily).
    Tracked separately from wh_action_queue (NBA customer-state).
    Returns number of rows processed.
    """
    if not rows:
        return 0

    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    # Exclude both PK columns from the SET clause
    update_set = ", ".join(
        f"{c} = excluded.{c}" for c in cols
        if c not in ("product_key", "customer_key")
    )

    sql = (
        f"INSERT INTO wh_deadstock_target ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(product_key, customer_key) DO UPDATE SET {update_set}"
    )

    values = [tuple(row.get(c) for c in cols) for row in rows]
    with conn:
        # True full-replace: the mart is the complete snapshot each run, so rows
        # that dropped out of it (now-excluded B2B accounts, resolved SKUs, etc.)
        # must be cleared — upsert alone would leave them stale in cache.
        # Guarded by the empty-rows check above so a transient empty fetch can
        # never wipe the table.
        conn.execute("DELETE FROM wh_deadstock_target")
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
