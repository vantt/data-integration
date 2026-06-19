"""hug_token operations — mint (pre-print) + claim (bind) + queries.

Pure data-access over hug.db. No HTTP, no edge concerns (the D1 push lives in
d1_push.py and is invoked by the claim caller after a successful local bind).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from hug.tokens import generate_token

# Generous safety cap on collision retries. With a 7.8e17 keyspace a collision
# is effectively never; the cap only guards against a corrupt/looping caller.
_MAX_COLLISION_RETRIES = 16


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def mint_batch(
    conn: sqlite3.Connection,
    count: int,
    *,
    batch_id: str,
    op_type: str = "package_insert",
) -> list[str]:
    """Generate `count` unique tokens, insert as status='printed', return them.

    Uniqueness is enforced by the UNIQUE index — on the rare collision the
    INSERT raises IntegrityError and we regenerate that one token. The whole
    batch commits atomically so a partial failure leaves no orphan rows.
    """
    if count <= 0:
        raise ValueError("count must be >= 1")

    minted: list[str] = []
    created = _utc_now()
    try:
        for _ in range(count):
            for attempt in range(_MAX_COLLISION_RETRIES):
                token = generate_token()
                try:
                    conn.execute(
                        "INSERT INTO hug_token (token, op_type, status, batch_id, created_at) "
                        "VALUES (?, ?, 'printed', ?, ?)",
                        (token, op_type, batch_id, created),
                    )
                    minted.append(token)
                    break
                except sqlite3.IntegrityError:
                    if attempt == _MAX_COLLISION_RETRIES - 1:
                        raise RuntimeError(
                            "token collision retries exhausted — keyspace anomaly"
                        )
                    continue
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return minted


def get_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    """Return the hug_token row for `token`, or None."""
    cur = conn.execute("SELECT * FROM hug_token WHERE token = ?", (token,))
    return cur.fetchone()


def list_batch(conn: sqlite3.Connection, batch_id: str) -> list[sqlite3.Row]:
    """Return all rows in a mint batch, ordered by creation."""
    cur = conn.execute(
        "SELECT * FROM hug_token WHERE batch_id = ? ORDER BY created_at, token",
        (batch_id,),
    )
    return cur.fetchall()


def list_recent_batches(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    """Return recent batches with their token counts (for the print picker)."""
    cur = conn.execute(
        "SELECT batch_id, COUNT(*) AS n, MIN(created_at) AS created_at "
        "FROM hug_token WHERE batch_id IS NOT NULL "
        "GROUP BY batch_id ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    return cur.fetchall()


def bind_token(
    conn: sqlite3.Connection,
    token: str,
    *,
    order_code: str,
    op_type: str = "package_insert",
    is_gift: bool = False,
    channel: str | None = None,
    campaign_hint: str | None = None,
) -> sqlite3.Row:
    """Bind a printed token to a Sapo order_code (claim). Returns the bound row.

    Idempotent-ish: re-binding the SAME token to the SAME order_code is allowed
    (updates attributes, refreshes bound_at). Binding an already-bound token to
    a DIFFERENT order_code raises — operators must mint a new tem instead.
    order->customer_id resolution happens ASYNC in the pipeline, not here.
    """
    row = get_token(conn, token)
    if row is None:
        raise KeyError(f"unknown token: {token}")
    if row["status"] == "bound" and row["order_code"] and row["order_code"] != order_code:
        raise ValueError(
            f"token already bound to a different order ({row['order_code']})"
        )

    bound_at = _utc_now()
    conn.execute(
        "UPDATE hug_token SET "
        "  status='bound', order_code=?, op_type=?, is_gift=?, "
        "  channel=COALESCE(?, channel), campaign_hint=COALESCE(?, campaign_hint), "
        "  bound_at=? "
        "WHERE token=?",
        (
            order_code,
            op_type,
            1 if is_gift else 0,
            channel,
            campaign_hint,
            bound_at,
            token,
        ),
    )
    conn.commit()
    return get_token(conn, token)  # type: ignore[return-value]


def mark_pushed(conn: sqlite3.Connection, token: str) -> None:
    """Record that a bound token has been pushed to the D1 edge cache."""
    conn.execute(
        "UPDATE hug_token SET pushed_at=? WHERE token=?",
        (_utc_now(), token),
    )
    conn.commit()


def counts_by_status(conn: sqlite3.Connection) -> dict[str, int]:
    """Return {status: count} across the whole master (for ops/health)."""
    cur = conn.execute("SELECT status, COUNT(*) AS n FROM hug_token GROUP BY status")
    return {r["status"]: r["n"] for r in cur.fetchall()}
