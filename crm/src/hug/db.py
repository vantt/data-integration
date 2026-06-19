"""hug.db connection + schema bootstrap.

Python-owned SQLite master for the Hug token lifecycle. Separate file from
crm.db (distinct lifecycle, offline mint/print, claim station, one-way edge
push). Single embedded schema applied idempotently on open — Hug has one table
so a full migration chain would be over-engineering (KISS).

Conventions mirror crm.db: WAL, busy_timeout, UTC ISO-8601 stored as TEXT.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from hug.config import hug_db_path

# hug_token = local MASTER (brain). Holds the full lifecycle for every token:
#   printed  — minted + (to be) printed, not yet attached to an order
#   bound    — claimed against a Sapo order_code at the claim station
# customer_id is resolved ASYNC later by the pipeline (order_code -> customer),
# never at claim time, so it stays nullable here.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS hug_token (
    token         TEXT PRIMARY KEY,                 -- random 12-char base32 (opaque)
    customer_id   TEXT,                             -- nullable; resolved async from order_code
    op_type       TEXT NOT NULL DEFAULT 'package_insert',
    order_code    TEXT,                             -- Sapo order code (set at claim)
    channel       TEXT,
    ship_date     TEXT,                             -- UTC ISO-8601 or YYYY-MM-DD
    sku           TEXT,
    campaign_hint TEXT,
    is_gift       INTEGER NOT NULL DEFAULT 0,       -- 0/1; feeds identity bridge
    status        TEXT NOT NULL DEFAULT 'printed',  -- printed -> bound
    batch_id      TEXT,                             -- mint batch grouping
    pushed_at     TEXT,                             -- when row was pushed to D1 (null = not yet)
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    bound_at      TEXT
);

-- PRIMARY KEY already gives a UNIQUE index on token; this explicit one documents
-- the collision-detection contract the mint loop relies on.
CREATE UNIQUE INDEX IF NOT EXISTS idx_hug_token_unique ON hug_token(token);
CREATE INDEX IF NOT EXISTS idx_hug_token_batch  ON hug_token(batch_id);
CREATE INDEX IF NOT EXISTS idx_hug_token_status ON hug_token(status);
CREATE INDEX IF NOT EXISTS idx_hug_token_order  ON hug_token(order_code);
"""

_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA synchronous=NORMAL",
)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open (creating if absent) hug.db, apply pragmas + schema, return the conn.

    Caller owns the connection lifecycle (use as a context manager or close()).
    """
    path = db_path or hug_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs sync route bodies in a threadpool, so
    # the long-lived connection is touched from worker threads. Mirrors the CRM
    # crm.db connection; single-writer discipline is preserved by design (one
    # connection, short claim transactions). CLI callers use the conn in one
    # thread, so this flag is harmless there.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    for stmt in _PRAGMAS:
        conn.execute(stmt)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn
