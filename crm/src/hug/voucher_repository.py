"""crm_hug_voucher CRUD — local issuance ledger operations.

Pure data-access over crm.db (single-writer discipline: caller controls the
connection lifecycle; functions commit their own writes).

The local CRM is the authoritative master for voucher issuance state.
The edge D1 hug_voucher table is a deferred projection and is NOT written here.

Functions:
  record_issuance  — idempotent INSERT OR IGNORE; safe to call twice for same PK
  get_issuance     — fetch one row by (code, customer_id)
  list_unredeemed  — all rows where redeemed_at IS NULL (used by redeem matcher)
  mark_redeemed    — set redeemed_at + order_code on a specific (code, customer_id)
  attribution_rows — backing query for v_hug_voucher_attribution per campaign
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def record_issuance(
    conn: sqlite3.Connection,
    *,
    code: str,
    customer_id: str,
    campaign_id: str,
    token: str | None = None,
    min_order: int | None = None,
    sku_guard: str | None = None,
    issued_at: str | None = None,
) -> bool:
    """Insert a voucher issuance row.  Idempotent: duplicate (code, customer_id)
    is silently ignored (INSERT OR IGNORE).

    Returns True if the row was newly inserted, False if it already existed.

    Args:
        code:        Campaign voucher code (e.g. "HUG50").
        customer_id: CRM customer identifier.
        campaign_id: Campaign that generated this issuance.
        token:       hug_token that triggered the issuance (may be None).
        min_order:   Minimum order value in VND from campaign offer (informational).
        sku_guard:   JSON list of excluded SKUs (informational).
        issued_at:   ISO-8601 UTC timestamp; defaults to now.
    """
    if not code:
        raise ValueError("code must be a non-empty string")
    if not customer_id:
        raise ValueError("customer_id must be a non-empty string")
    if not campaign_id:
        raise ValueError("campaign_id must be a non-empty string")

    ts = issued_at or _utc_now()

    cur = conn.execute(
        """
        INSERT OR IGNORE INTO crm_hug_voucher
            (code, customer_id, token, campaign_id, min_order, sku_guard, issued_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (code, customer_id, token, campaign_id, min_order, sku_guard, ts),
    )
    conn.commit()
    return cur.rowcount == 1


def mark_redeemed(
    conn: sqlite3.Connection,
    *,
    code: str,
    customer_id: str,
    order_code: str,
    redeemed_at: str | None = None,
) -> bool:
    """Set redeemed_at and order_code on an existing issuance row.

    Only updates rows where redeemed_at IS NULL to prevent double-marking.
    Returns True if the row was updated, False if already redeemed or not found.

    Args:
        code:        Voucher code.
        customer_id: CRM customer identifier.
        order_code:  Sapo order_code of the redeeming order.
        redeemed_at: ISO-8601 UTC timestamp; defaults to now.
    """
    if not order_code:
        raise ValueError("order_code must be a non-empty string")

    ts = redeemed_at or _utc_now()

    cur = conn.execute(
        """
        UPDATE crm_hug_voucher
           SET redeemed_at = ?, order_code = ?
         WHERE code = ? AND customer_id = ? AND redeemed_at IS NULL
        """,
        (ts, order_code, code, customer_id),
    )
    conn.commit()
    return cur.rowcount == 1


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_issuance(
    conn: sqlite3.Connection,
    code: str,
    customer_id: str,
) -> sqlite3.Row | None:
    """Return the issuance row for (code, customer_id), or None if not found."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM crm_hug_voucher WHERE code = ? AND customer_id = ?",
        (code, customer_id),
    )
    return cur.fetchone()


def list_unredeemed(
    conn: sqlite3.Connection,
    campaign_id: str | None = None,
) -> list[sqlite3.Row]:
    """Return all rows where redeemed_at IS NULL (pending redeem matcher pass).

    Args:
        campaign_id: If provided, restrict to one campaign.  None returns all.
    """
    conn.row_factory = sqlite3.Row
    if campaign_id is not None:
        cur = conn.execute(
            "SELECT * FROM crm_hug_voucher"
            " WHERE redeemed_at IS NULL AND campaign_id = ?"
            " ORDER BY issued_at",
            (campaign_id,),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM crm_hug_voucher"
            " WHERE redeemed_at IS NULL"
            " ORDER BY issued_at",
        )
    return cur.fetchall()


def attribution_rows(
    conn: sqlite3.Connection,
    campaign_id: str | None = None,
) -> list[sqlite3.Row]:
    """Query v_hug_voucher_attribution for issued/redeemed counts.

    Args:
        campaign_id: If provided, restrict to one campaign.  None returns all.
    Returns rows with columns: campaign_id, code, issued, redeemed, redeem_rate_pct.
    """
    conn.row_factory = sqlite3.Row
    if campaign_id is not None:
        cur = conn.execute(
            "SELECT * FROM v_hug_voucher_attribution WHERE campaign_id = ?",
            (campaign_id,),
        )
    else:
        cur = conn.execute("SELECT * FROM v_hug_voucher_attribution")
    return cur.fetchall()
