"""voucher_issuer.py — Local issuance writer for Hug voucher campaigns.

Reads new opt-in rows from mart_hug_optin (olap.duckdb, read-only), cross-joins
with crm_hug_campaign and crm_identity_link, and writes one row per qualifying
opt-in to crm_hug_voucher via record_issuance (INSERT OR IGNORE — idempotent).

Qualifying conditions (all must hold):
  1. opt-in.campaign_id is not NULL
  2. crm_hug_campaign.offer_ref is not NULL (i.e. it's a voucher campaign)
  3. crm_identity_link has a resolved_customer_id for this token

Unresolved opt-ins (condition 3 fails) are NOT written and NOT advanced past
the watermark — they are retried on the next /admin/refresh cycle after
hug_resolve has had another pass.

Pre-deploy resilience: if olap.duckdb or mart_hug_optin is absent the function
returns 0 cleanly so it never aborts the refresh.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from hug.identity_resolver_io import load_watermark, save_watermark
from hug.voucher_repository import record_issuance

log = logging.getLogger(__name__)


def _fetch_new_optins_with_campaign(olap_path: str, since_ts: str) -> list[dict]:
    """Open olap.duckdb read-only and return opt-ins that have a campaign_id.

    Returns rows ordered by event_ts ASC so the watermark advances monotonically.
    Catches CatalogException (mart absent before first ingest) and returns [].
    """
    import duckdb

    con = duckdb.connect(olap_path, read_only=True)
    try:
        try:
            rows = con.execute(
                """
                SELECT
                    token,
                    campaign_id,
                    CAST(event_ts AS VARCHAR) AS event_ts
                FROM main_marts.mart_hug_optin
                WHERE campaign_id IS NOT NULL
                  AND CAST(event_ts AS VARCHAR) > ?
                ORDER BY event_ts ASC
                """,
                [since_ts],
            ).fetchall()
        except duckdb.CatalogException:
            log.info(
                "voucher_issuer: mart_hug_optin absent from serving db (pre-deploy) — 0 rows"
            )
            return []
        cols = ["token", "campaign_id", "event_ts"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        con.close()


def _get_offer_ref(crm_conn: sqlite3.Connection, campaign_id: str) -> str | None:
    """Return offer_ref for campaign_id, or None if campaign absent / no offer."""
    row = crm_conn.execute(
        "SELECT offer_ref FROM crm_hug_campaign WHERE campaign_id = ?",
        (campaign_id,),
    ).fetchone()
    if row is None:
        log.warning("voucher_issuer: campaign_id=%r not found in crm_hug_campaign — skipping", campaign_id)
        return None
    offer_ref = row[0]
    if not offer_ref:
        log.debug("voucher_issuer: campaign_id=%r has no offer_ref — skipping", campaign_id)
        return None
    return offer_ref


def _get_resolved_customer(crm_conn: sqlite3.Connection, token: str) -> str | None:
    """Return the resolved_customer_id for a token, or None if unresolved.

    Prefers crm_identity_link (status='linked') over hug_token.customer_id so
    the identity-bridge resolution policy is authoritative.  If crm_identity_link
    has no linked row, the opt-in is considered unresolved and will be retried.
    """
    row = crm_conn.execute(
        """
        SELECT resolved_customer_id
        FROM crm_identity_link
        WHERE token = ? AND status = 'linked' AND resolved_customer_id IS NOT NULL
        LIMIT 1
        """,
        (token,),
    ).fetchone()
    return row[0] if row else None


def issue_vouchers(
    crm_conn: sqlite3.Connection,
    olap_path: str,
    watermark_path: str,
    *,
    optin_rows: list[dict] | None = None,
) -> int:
    """Issue vouchers for new opt-ins that have a resolved customer and a campaign offer.

    Reads mart_hug_optin from olap.duckdb since the last watermark, matches each
    row against crm_hug_campaign and crm_identity_link, and writes qualifying rows
    to crm_hug_voucher via INSERT OR IGNORE (idempotent on PK (code, customer_id)).

    Args:
        crm_conn:       Open sqlite3.Connection to crm.db (read+write).
        olap_path:      Path to olap.duckdb (opened read-only internally).
        watermark_path: Path to the JSON watermark file (created if absent).
        optin_rows:     Inject rows directly (unit tests — bypasses olap.duckdb).

    Returns:
        Number of new ledger rows inserted (0 if all duplicates or none qualify).
    """
    wm_path = Path(watermark_path)
    since = load_watermark(wm_path)

    if optin_rows is None:
        rows = _fetch_new_optins_with_campaign(olap_path, since)
    else:
        # Test injection: filter by watermark + must have campaign_id
        rows = [
            r for r in optin_rows
            if (r.get("event_ts") or "") > since and r.get("campaign_id")
        ]

    if not rows:
        log.debug("voucher_issuer: no new opt-ins with campaign_id since %s", since or "beginning")
        return 0

    inserted = 0
    latest_eligible_ts = since  # tracks max ts of rows we can advance past

    for row in rows:
        token = row["token"]
        campaign_id = row["campaign_id"]
        event_ts = row.get("event_ts") or ""

        offer_ref = _get_offer_ref(crm_conn, campaign_id)
        if offer_ref is None:
            # No offer on this campaign — advance past it (nothing to retry)
            if event_ts > latest_eligible_ts:
                latest_eligible_ts = event_ts
            continue

        customer_id = _get_resolved_customer(crm_conn, token)
        if customer_id is None:
            # Identity not yet resolved — do NOT advance watermark past this row;
            # hug_resolve will resolve it on a future cycle and the issuer retries.
            log.debug(
                "voucher_issuer: token=%r unresolved — deferring (will retry next cycle)",
                token,
            )
            continue  # intentionally skip advancing latest_eligible_ts

        newly_written = record_issuance(
            crm_conn,
            code=offer_ref,
            customer_id=customer_id,
            campaign_id=campaign_id,
            token=token,
            issued_at=event_ts or None,
        )
        if newly_written:
            inserted += 1
            log.debug(
                "voucher_issuer: issued code=%r to customer=%r (campaign=%r token=%r)",
                offer_ref, customer_id, campaign_id, token,
            )

        if event_ts > latest_eligible_ts:
            latest_eligible_ts = event_ts

    if latest_eligible_ts > since:
        save_watermark(wm_path, latest_eligible_ts)

    log.info(
        "voucher_issuer: %d new vouchers issued; watermark → %s",
        inserted, latest_eligible_ts or since or "unchanged",
    )
    return inserted
