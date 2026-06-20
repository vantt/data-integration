"""identity_resolver_io.py — I/O helpers for the Hug identity resolver.

Contains three concerns kept separate from the policy logic:
  1. Watermark: persist/load the last-processed event_ts (simple JSON file).
  2. olap.duckdb: fetch new opt-in rows from mart_hug_optin (read-only).
  3. crm_identity_link: upsert resolution outcomes to crm.db.
  4. crm_party_identity: contact-quality upgrade helpers (never downgrade).
  5. hug.db: is_gift and buyer lookup helpers.

All DB writes use ? placeholders — no f-string interpolation of user data.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from application.party_service import _utc_now

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contactability ladder — imported here so callers share one definition
# ---------------------------------------------------------------------------
_LADDER: list[str] = ["masked", "zalo_follower", "unverified", "verified"]

# Confidence heuristics (simple, documented per §8)
CONF_EXACT = 1.0    # phone matches buyer's own identity — highest certainty
CONF_ASSIGN = 1.0   # unclaimed phone + masked buyer — happy path, low risk
CONF_REVIEW = 0.5   # conflict or cross-signal — routed to needs_review


def ladder_rank(quality: str) -> int:
    """Return the rank of a contact_quality value in the non-decreasing ladder."""
    try:
        return _LADDER.index(quality)
    except ValueError:
        return 0  # unknown values treated as masked — safe fallback


def upgrade_quality(current: str, proposed: str) -> str:
    """Return the higher of current and proposed quality (never downgrade)."""
    return proposed if ladder_rank(proposed) > ladder_rank(current) else current


# ---------------------------------------------------------------------------
# Watermark helpers
# ---------------------------------------------------------------------------
_WATERMARK_KEY = "last_event_ts"


def load_watermark(path: Path) -> str:
    """Return the last-processed event_ts string, or empty string if none."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get(_WATERMARK_KEY, "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def save_watermark(path: Path, ts: str) -> None:
    """Persist the latest processed event_ts."""
    path.write_text(json.dumps({_WATERMARK_KEY: ts}), encoding="utf-8")


# ---------------------------------------------------------------------------
# olap.duckdb fetch
# ---------------------------------------------------------------------------

def fetch_new_optins(olap_path: str, since_ts: str) -> list[dict]:
    """Open olap.duckdb read-only, return new opt-in rows from mart_hug_optin.

    Rows are ordered by event_ts ASC so the watermark advances monotonically.
    Returns list of dicts: token, buyer_customer_id, phone, zalo_uid, name,
    consent_json, event_ts.
    """
    import duckdb  # local import — excluded from unit tests that inject rows directly

    con = duckdb.connect(olap_path, read_only=True)
    try:
        try:
            rows = con.execute(
                """
                SELECT
                    token, buyer_customer_id, phone, zalo_uid, name, consent_json,
                    CAST(event_ts AS VARCHAR) AS event_ts
                FROM main_marts.mart_hug_optin
                WHERE CAST(event_ts AS VARCHAR) > ?
                ORDER BY event_ts ASC
                """,
                [since_ts],
            ).fetchall()
        except duckdb.CatalogException:
            # mart_hug_optin is absent from the serving DB until the first real
            # opt-in is ingested (the serving builder skips an empty-folder mart).
            # No data to resolve yet — return cleanly instead of reding the refresh.
            log.info("fetch_new_optins: mart_hug_optin not in serving db yet — 0 rows")
            return []
        cols = ["token", "buyer_customer_id", "phone", "zalo_uid", "name", "consent_json", "event_ts"]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        con.close()


# ---------------------------------------------------------------------------
# crm_identity_link persistence
# ---------------------------------------------------------------------------

_SQL_UPSERT_LINK = """
INSERT INTO crm_identity_link
    (token, buyer_customer_id, scanner_phone, scanner_zalo_uid,
     resolved_customer_id, confidence, status, ts)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(token, scanner_phone) DO UPDATE SET
    buyer_customer_id    = excluded.buyer_customer_id,
    scanner_zalo_uid     = excluded.scanner_zalo_uid,
    resolved_customer_id = excluded.resolved_customer_id,
    confidence           = excluded.confidence,
    status               = excluded.status,
    ts                   = excluded.ts
"""


def upsert_link(
    crm_conn: sqlite3.Connection,
    *,
    token: str,
    buyer_customer_id: Optional[str],
    scanner_phone: Optional[str],
    scanner_zalo_uid: Optional[str],
    resolved_customer_id: Optional[str],
    confidence: float,
    status: str,
) -> None:
    """Write or update a crm_identity_link row (idempotent on token+phone)."""
    crm_conn.execute(
        _SQL_UPSERT_LINK,
        (
            token,
            buyer_customer_id or None,
            scanner_phone or None,
            scanner_zalo_uid or None,
            resolved_customer_id or None,
            confidence,
            status,
            _utc_now(),
        ),
    )


# ---------------------------------------------------------------------------
# crm_party_identity contact-quality helpers
# ---------------------------------------------------------------------------

def get_party_contact_quality(crm_conn: sqlite3.Connection, party_id: str) -> str:
    """Return the best current contact_quality for a party across all its identities."""
    rows = crm_conn.execute(
        "SELECT contact_quality FROM crm_party_identity WHERE party_id = ?",
        (party_id,),
    ).fetchall()
    if not rows:
        return "masked"
    return max((r[0] or "masked" for r in rows), key=ladder_rank)


def upgrade_party_contact_quality(
    crm_conn: sqlite3.Connection,
    party_id: str,
    proposed: str,
) -> None:
    """Upgrade identity rows for party_id to proposed quality if higher.

    Never downgrades any existing row. Applies to all identities for the party.
    """
    rows = crm_conn.execute(
        "SELECT identity_id, contact_quality FROM crm_party_identity WHERE party_id = ?",
        (party_id,),
    ).fetchall()
    for identity_id, current_quality in rows:
        new_quality = upgrade_quality(current_quality or "masked", proposed)
        if new_quality != (current_quality or "masked"):
            crm_conn.execute(
                "UPDATE crm_party_identity SET contact_quality = ? WHERE identity_id = ?",
                (new_quality, identity_id),
            )


def add_contact_identities(
    crm_conn: sqlite3.Connection,
    party_id: str,
    phone: Optional[str],
    quality: str,
    zalo_uid: Optional[str] = None,
) -> None:
    """Add phone and/or zalo_uid identities to party_id (INSERT OR IGNORE on dup).

    Does NOT delete existing identities — multi-identity model (§8 C6).
    phone=None skips the phone insert (Zalo-only C5 path).
    """
    now = _utc_now()
    if phone:
        crm_conn.execute(
            """
            INSERT OR IGNORE INTO crm_party_identity
                (identity_id, party_id, source_system, identity_type, identity_value,
                 confidence, is_primary, source_contact_quality, contact_quality, created_at)
            VALUES (?, ?, 'hug', 'phone', ?, ?, 0, ?, ?, ?)
            """,
            (str(uuid.uuid4()), party_id, phone, CONF_ASSIGN, quality, quality, now),
        )
    if zalo_uid:
        crm_conn.execute(
            """
            INSERT OR IGNORE INTO crm_party_identity
                (identity_id, party_id, source_system, identity_type, identity_value,
                 confidence, is_primary, source_contact_quality, contact_quality, created_at)
            VALUES (?, ?, 'hug', 'zalo_uid', ?, ?, 0, 'zalo_follower', 'zalo_follower', ?)
            """,
            (str(uuid.uuid4()), party_id, zalo_uid, CONF_ASSIGN, now),
        )


# ---------------------------------------------------------------------------
# hug.db helpers
# ---------------------------------------------------------------------------

def get_is_gift(hug_conn: sqlite3.Connection, token: str) -> bool:
    """Return True if the token was flagged as a gift at claim time."""
    row = hug_conn.execute(
        "SELECT is_gift FROM hug_token WHERE token = ?", (token,)
    ).fetchone()
    return bool(row[0]) if row else False


def resolve_buyer_party(
    crm_conn: sqlite3.Connection,
    hug_conn: sqlite3.Connection,
    token: str,
    buyer_customer_id: Optional[str],
) -> Optional[str]:
    """Return the CRM party_id for the buyer of this token.

    Preference order (§8):
      1. opt-in.buyer_customer_id (Sapo customer_id on the opt-in event)
      2. derive from hug_token.order_code → wh_order_hdr.customer_id in cache.db

    Returns None when unresolvable (token not bound, order not yet in warehouse).
    """
    # 1. Direct buyer_customer_id from opt-in payload
    if buyer_customer_id:
        party = crm_conn.execute(
            "SELECT party_id FROM crm_party_identity"
            " WHERE identity_type = 'sapo_customer' AND identity_value = ? LIMIT 1",
            (str(buyer_customer_id),),
        ).fetchone()
        if party:
            return party[0]

    # 2. Derive from hug_token.order_code → cache.wh_order_hdr
    token_row = hug_conn.execute(
        "SELECT order_code FROM hug_token WHERE token = ?", (token,)
    ).fetchone()
    if not token_row or not token_row[0]:
        return None

    order_code = token_row[0]
    try:
        order_row = crm_conn.execute(
            "SELECT customer_id FROM cache.wh_order_hdr WHERE order_code = ? LIMIT 1",
            (order_code,),
        ).fetchone()
    except sqlite3.OperationalError:
        # wh_order_hdr not yet populated (pipeline hasn't run)
        log.warning("wh_order_hdr not available for order_code=%s", order_code)
        return None

    if not order_row or not order_row[0]:
        return None

    derived_customer_id = str(order_row[0])
    party = crm_conn.execute(
        "SELECT party_id FROM crm_party_identity"
        " WHERE identity_type = 'sapo_customer' AND identity_value = ? LIMIT 1",
        (derived_customer_id,),
    ).fetchone()
    return party[0] if party else None
