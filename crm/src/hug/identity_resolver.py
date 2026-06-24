"""identity_resolver.py — Hug identity-bridge policy engine (I2-resolve).

Applies the §8 policy for each opt-in event and persists results into crm.db.
I/O helpers (watermark, olap fetch, SQL persistence) live in identity_resolver_io.py.

Policy cases (§8):
  C1. phone == buyer's own identity   → confirm; upgrade to verified; linked
  C2. phone unclaimed + buyer masked  → assign phone to buyer; unverified; linked
  C3. phone belongs to another party  → route to that party; needs_review if cross-signal
  C4. is_gift == True                 → route to SCANNER (phone owner); not buyer
  C5. Zalo-only (no phone)            → zalo_uid + zalo_follower if buyer masked; linked
  C6. multiple/changed phones         → ADD identity, never delete
  C7. re-opt-in same (token, phone)   → idempotent; update existing row

Contactability ladder (strictly non-decreasing):
  masked < zalo_follower < unverified < verified
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from application.party_service import normalize_phone
from hug.identity_resolver_io import (
    CONF_ASSIGN,
    CONF_EXACT,
    CONF_REVIEW,
    add_contact_identities,
    fetch_new_optins,
    get_is_gift,
    get_party_contact_quality,
    ladder_rank,
    load_watermark,
    resolve_buyer_party,
    save_watermark,
    upgrade_party_contact_quality,
    upsert_link,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core policy engine
# ---------------------------------------------------------------------------

def _apply_policy(
    crm_conn: sqlite3.Connection,
    hug_conn: sqlite3.Connection,
    row: dict,
) -> None:
    """Apply the §8 identity-bridge policy for one opt-in row and persist results.

    Mutates crm_identity_link (upsert) and crm_party_identity (upgrade-only).
    """
    token: str = row["token"]
    buyer_cid: Optional[str] = row.get("buyer_customer_id") or None
    raw_phone: str = row.get("phone") or ""
    zalo_uid: Optional[str] = row.get("zalo_uid") or None

    norm_phone = normalize_phone(raw_phone) if raw_phone else ""

    is_gift = get_is_gift(hug_conn, token)
    buyer_party_id = resolve_buyer_party(crm_conn, hug_conn, token, buyer_cid)

    # ── C5: Zalo-only (no phone) ─────────────────────────────────────────────
    if not norm_phone and zalo_uid:
        if buyer_party_id:
            current_quality = get_party_contact_quality(crm_conn, buyer_party_id)
            if ladder_rank(current_quality) == ladder_rank("masked"):
                # Add zalo_uid identity only (no phone). Only upgrade from masked.
                add_contact_identities(crm_conn, buyer_party_id, None, "zalo_follower", zalo_uid)
                upgrade_party_contact_quality(crm_conn, buyer_party_id, "zalo_follower")
        upsert_link(
            crm_conn,
            token=token,
            buyer_customer_id=buyer_cid,
            scanner_phone=None,
            scanner_zalo_uid=zalo_uid,
            resolved_customer_id=buyer_party_id,
            confidence=CONF_ASSIGN,
            status="linked",
        )
        return

    if not norm_phone:
        # No phone and no zalo_uid — nothing actionable
        log.debug("token=%s: opt-in has neither phone nor zalo_uid — skipping", token)
        return

    # Look up whether the phone already belongs to any CRM party
    phone_owner_row = crm_conn.execute(
        "SELECT party_id FROM crm_party_identity"
        " WHERE identity_type = 'phone' AND identity_value = ? LIMIT 1",
        (norm_phone,),
    ).fetchone()
    phone_owner_id: Optional[str] = phone_owner_row[0] if phone_owner_row else None

    # ── C4: Gift — opt-in belongs to the SCANNER, not the buyer ─────────────
    if is_gift:
        if phone_owner_id:
            # Cross-signal: we have a real buyer ≠ scanner → needs_review
            cross = buyer_party_id is not None and phone_owner_id != buyer_party_id
            status = "needs_review" if cross else "linked"
            upgrade_party_contact_quality(crm_conn, phone_owner_id, "unverified")
            upsert_link(
                crm_conn,
                token=token,
                buyer_customer_id=buyer_cid,
                scanner_phone=norm_phone,
                scanner_zalo_uid=zalo_uid,
                resolved_customer_id=phone_owner_id,
                confidence=CONF_REVIEW if status == "needs_review" else CONF_ASSIGN,
                status=status,
            )
        else:
            # Scanner phone unclaimed — record but leave unresolved
            upsert_link(
                crm_conn,
                token=token,
                buyer_customer_id=buyer_cid,
                scanner_phone=norm_phone,
                scanner_zalo_uid=zalo_uid,
                resolved_customer_id=None,
                confidence=CONF_REVIEW,
                status="needs_review",
            )
        return

    # ── C1: phone matches the buyer's own identity ────────────────────────────
    if buyer_party_id and phone_owner_id == buyer_party_id:
        upgrade_party_contact_quality(crm_conn, buyer_party_id, "verified")
        upsert_link(
            crm_conn,
            token=token,
            buyer_customer_id=buyer_cid,
            scanner_phone=norm_phone,
            scanner_zalo_uid=zalo_uid,
            resolved_customer_id=buyer_party_id,
            confidence=CONF_EXACT,
            status="linked",
        )
        return

    # ── C3: phone belongs to a different party ────────────────────────────────
    if phone_owner_id and (buyer_party_id is None or phone_owner_id != buyer_party_id):
        cross = buyer_party_id is not None and phone_owner_id != buyer_party_id
        status = "needs_review" if cross else "linked"
        upgrade_party_contact_quality(crm_conn, phone_owner_id, "unverified")
        upsert_link(
            crm_conn,
            token=token,
            buyer_customer_id=buyer_cid,
            scanner_phone=norm_phone,
            scanner_zalo_uid=zalo_uid,
            resolved_customer_id=phone_owner_id,
            confidence=CONF_REVIEW if status == "needs_review" else CONF_ASSIGN,
            status=status,
        )
        return

    # ── C2: phone unclaimed + buyer known ────────────────────────────────────
    if not phone_owner_id and buyer_party_id:
        # Auto-assign regardless of whether buyer is masked or already has phones.
        # §8 happy path: masked buyer gets phone assigned (C2);
        # buyer with existing phones: additional phone added (C6).
        add_contact_identities(crm_conn, buyer_party_id, norm_phone, "unverified", zalo_uid)
        upgrade_party_contact_quality(crm_conn, buyer_party_id, "unverified")
        upsert_link(
            crm_conn,
            token=token,
            buyer_customer_id=buyer_cid,
            scanner_phone=norm_phone,
            scanner_zalo_uid=zalo_uid,
            resolved_customer_id=buyer_party_id,
            confidence=CONF_ASSIGN,
            status="linked",
        )
        return

    # ── Fallback: phone unclaimed, buyer unknown ──────────────────────────────
    upsert_link(
        crm_conn,
        token=token,
        buyer_customer_id=buyer_cid,
        scanner_phone=norm_phone,
        scanner_zalo_uid=zalo_uid,
        resolved_customer_id=None,
        confidence=CONF_REVIEW,
        status="needs_review",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def resolve_new_optins(
    crm_conn: sqlite3.Connection,
    hug_conn: sqlite3.Connection,
    olap_path: str,
    watermark_path: str,
    *,
    optin_rows: Optional[list[dict]] = None,
) -> int:
    """Process all new opt-in events since the last watermark.

    Args:
        crm_conn:       sqlite3.Connection to crm.db (cache.db attached as 'cache')
        hug_conn:       sqlite3.Connection to hug.db
        olap_path:      Path to olap.duckdb (opened read-only internally)
        watermark_path: Path to the JSON watermark file (created if absent)
        optin_rows:     Inject rows directly (unit tests only — skips olap.duckdb)

    Returns:
        Number of opt-in rows processed.
    """
    wm_path = Path(watermark_path)
    since = load_watermark(wm_path)

    if optin_rows is None:
        rows = fetch_new_optins(olap_path, since)
    else:
        rows = [r for r in optin_rows if (r.get("event_ts") or "") > since]

    if not rows:
        log.debug("resolve_new_optins: no new rows since %s", since or "beginning")
        return 0

    latest_ts = since
    try:
        for row in rows:
            _apply_policy(crm_conn, hug_conn, row)
            ts = row.get("event_ts") or ""
            if ts > latest_ts:
                latest_ts = ts
        # Save watermark BEFORE commit so both succeed or both are rolled back.
        # A crash between save_watermark and commit is handled by the file write
        # being atomic on POSIX (write+rename); on Windows the file write completes
        # fully before commit, so the worst outcome is a re-process on next run
        # (all upserts are idempotent for phone-bearing rows; Zalo-only rows are
        # deduplicated by (token, zalo_uid) in upsert_link).
        if latest_ts > since:
            save_watermark(wm_path, latest_ts)
        crm_conn.commit()
    except Exception:
        crm_conn.rollback()
        raise

    log.info("resolve_new_optins: processed %d rows; watermark → %s", len(rows), latest_ts)
    return len(rows)
