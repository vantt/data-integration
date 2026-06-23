"""hug_token operations — mint (pre-print) + claim (bind) + queries.

Pure data-access over hug.db. No HTTP, no edge concerns (the D1 push lives in
d1_push.py and is invoked by the claim caller after a successful local bind).
"""
from __future__ import annotations

import json
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


class AlreadyBoundError(ValueError):
    """Raised when a token is already bound to a DIFFERENT session.

    This is a blocking condition: the operator trying to claim this token did
    not originate the original bind operation.  The caller should show a red
    "token claimed in another operation" message and refuse the bind.
    """


def bind_token(
    conn: sqlite3.Connection,
    token: str,
    *,
    order_code: str,
    is_gift: bool = False,
    channel: str | None = None,
    campaign_hint: str | None = None,
    bind_session_id: str | None = None,
    bind_attributes: dict | None = None,
) -> sqlite3.Row:
    """Bind a printed token to a Sapo order_code (claim). Returns the bound row.

    Idempotency rules (in precedence order):
    1. Already bound to a DIFFERENT order_code → ValueError (operator error; mint new sticker).
    2. Already bound, SAME session (bind_session_id match) → allow re-bind.
       Rationale: same-session rebind = mid-operation correction (staff re-scanned
       same token before moving on; overwriting is safe because it's the same op).
    3. Already bound, DIFFERENT session (both non-None, not equal) → AlreadyBoundError.
       Rationale: another operator's operation owns this token; blocking prevents
       accidental double-claim.
    4. Either side None → allow re-bind (form-POST/no-JS path sets no session).

    bind_attributes: optional dict of dynamic non-promoted fields (currently empty
    at MVP; future local-only metadata fields land here without schema change).
    Stored as JSON in bind_attributes column.

    order->customer_id resolution happens ASYNC in the pipeline, not here.
    """
    row = get_token(conn, token)
    if row is None:
        raise KeyError(f"unknown token: {token}")

    if row["status"] == "bound":
        # Guard 1: different order entirely
        if row["order_code"] and row["order_code"] != order_code:
            raise ValueError(
                f"token already bound to a different order ({row['order_code']})"
            )
        # Guard 2/3: session check
        stored_session = row["bind_session_id"]
        if stored_session and bind_session_id and stored_session != bind_session_id:
            # Different non-None sessions → another operator owns this bind
            raise AlreadyBoundError(
                "token already claimed in a different operation"
            )
        # Same session (or either side None) → fall through to UPDATE (re-bind)

    bound_at = _utc_now()
    # op_type is a MINT-time (batch) property of the physical sticker — do NOT
    # overwrite it at claim. Claim only sets order_code + is_gift.
    conn.execute(
        "UPDATE hug_token SET "
        "  status='bound', order_code=?, is_gift=?, "
        "  channel=COALESCE(?, channel), campaign_hint=COALESCE(?, campaign_hint), "
        "  bound_at=?, bind_session_id=?, bind_attributes=? "
        "WHERE token=?",
        (
            order_code,
            1 if is_gift else 0,
            channel,
            campaign_hint,
            bound_at,
            bind_session_id,
            json.dumps(bind_attributes or {}),
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
