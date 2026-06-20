"""voucher_redeem_matcher.py — Match redeemed Sapo coupon codes → crm_hug_voucher.

Reads fact_orders from olap.duckdb (read-only) for orders that carry a coupon
code (order_coupon_code IS NOT NULL).  For each such order, attempts an UPDATE
on crm_hug_voucher WHERE code = ? AND customer_id = ? AND redeemed_at IS NULL.

Match key: exact (customer_id, order_coupon_code) — we only attribute redemptions
for codes the CRM actually issued to that specific customer.  Organic Sapo coupon
use, or a different customer using the same shared code, simply won't match any
ledger row (correct: no HUG attribution for non-issued use).

Idempotency: the UPDATE WHERE redeemed_at IS NULL means already-redeemed rows
are silently skipped, preserving the first-seen redemption timestamp.

Pre-deploy resilience: if olap.duckdb or fact_orders is absent, the function
returns 0 and logs info — it never raises an exception that aborts the refresh.

Watermark: persisted to {CRM_DATA_DIR}/hug_redeem_watermark.json as
{"last_ordered_at": "<ISO-8601 UTC>"}.  On each run only orders with
ordered_at > watermark are scanned, bounding the work after the first pass.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from hug.identity_resolver_io import load_watermark, save_watermark

log = logging.getLogger(__name__)

# The watermark JSON key used by this module (distinct from other watermark files).
_WATERMARK_KEY = "last_ordered_at"


def _load_redeem_watermark(path: Path) -> str:
    """Load the last-processed ordered_at string, defaulting to epoch start."""
    if path.exists():
        import json
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get(_WATERMARK_KEY, "") or ""
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def _save_redeem_watermark(path: Path, ts: str) -> None:
    """Persist the latest processed ordered_at timestamp."""
    import json
    path.write_text(json.dumps({_WATERMARK_KEY: ts}), encoding="utf-8")


def _fetch_candidate_orders(olap_path: str, since_ts: str) -> list[dict]:
    """Open olap.duckdb read-only and return orders carrying a coupon code.

    Only returns rows with non-NULL customer_id (guest/masked orders cannot
    be attributed to a CRM ledger row).

    Returns rows ordered by ordered_at ASC so the watermark advances monotonically.
    Catches duckdb.CatalogException (fact_orders absent pre-deploy) and returns [].
    """
    import duckdb  # local import — excluded when tests inject rows directly

    con = duckdb.connect(olap_path, read_only=True)
    try:
        try:
            rows = con.execute(
                f"""
                SELECT
                    d.customer_id,
                    f.order_coupon_code   AS code,
                    f.order_code,
                    CAST(f.ordered_at AS VARCHAR) AS ordered_at
                FROM main_marts.fact_orders f
                -- fact_orders exposes only the surrogate customer_key; the raw
                -- Sapo customer_id (the key crm_hug_voucher is issued against)
                -- lives on dim_customers.
                JOIN main_marts.dim_customers d ON f.customer_key = d.customer_key
                WHERE f.order_coupon_code IS NOT NULL
                  AND d.customer_id IS NOT NULL
                  AND f.ordered_at > TIMESTAMPTZ '{since_ts or "1970-01-01T00:00:00Z"}'
                ORDER BY f.ordered_at ASC
                """
            ).fetchall()
        except duckdb.CatalogException:
            # fact_orders absent (extract-coupon not yet deployed, or empty serving DB).
            log.info(
                "voucher_redeem_matcher: fact_orders not in serving db yet — 0 candidates"
            )
            return []
        cols = ["customer_id", "code", "order_code", "ordered_at"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        con.close()


def match_redeemed_vouchers(
    crm_conn: sqlite3.Connection,
    olap_path: str,
    watermark_path: str,
    *,
    candidate_rows: list[dict] | None = None,
) -> int:
    """Scan new fact_orders for coupon codes matching issued crm_hug_voucher rows.

    For each candidate order, attempts to mark the matching voucher ledger row as
    redeemed (sets redeemed_at + order_code).  Already-redeemed rows are silently
    skipped (WHERE redeemed_at IS NULL in the UPDATE).

    Args:
        crm_conn:        Open sqlite3.Connection to crm.db (read+write).
        olap_path:       Path to olap.duckdb (opened read-only internally).
        watermark_path:  Path to the JSON watermark file (created if absent).
        candidate_rows:  Inject rows directly (unit tests — bypasses olap.duckdb).
                         Each dict must have: customer_id, code, order_code, ordered_at.

    Returns:
        Number of voucher rows newly marked as redeemed (0 if none matched).
    """
    wm_path = Path(watermark_path)
    since = _load_redeem_watermark(wm_path)

    if candidate_rows is None:
        rows = _fetch_candidate_orders(olap_path, since)
    else:
        # Test injection: apply watermark filter to mimic real behaviour.
        rows = [
            r for r in candidate_rows
            if (r.get("ordered_at") or "") > (since or "")
        ]

    if not rows:
        log.debug(
            "voucher_redeem_matcher: no candidate orders with coupon code since %s",
            since or "beginning",
        )
        return 0

    updated = 0
    latest_ts = since  # advance watermark to max ordered_at of scanned batch

    for row in rows:
        customer_id = row["customer_id"]
        code = row["code"]
        order_code = row["order_code"]
        ordered_at = row.get("ordered_at") or ""

        cur = crm_conn.execute(
            """
            UPDATE crm_hug_voucher
               SET redeemed_at = ?, order_code = ?
             WHERE code = ? AND customer_id = ? AND redeemed_at IS NULL
            """,
            (ordered_at, order_code, code, customer_id),
        )
        if cur.rowcount == 1:
            updated += 1
            log.debug(
                "voucher_redeem_matcher: marked code=%r customer=%r order=%r redeemed_at=%r",
                code, customer_id, order_code, ordered_at,
            )

        if ordered_at > (latest_ts or ""):
            latest_ts = ordered_at

    crm_conn.commit()

    if latest_ts and latest_ts > (since or ""):
        _save_redeem_watermark(wm_path, latest_ts)

    log.info(
        "voucher_redeem_matcher: %d vouchers marked redeemed; watermark → %s",
        updated, latest_ts or since or "unchanged",
    )
    return updated
