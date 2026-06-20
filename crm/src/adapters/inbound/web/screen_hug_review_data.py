"""screen_hug_review_data.py — pure data-layer helpers for the Hug CS review queue.

No FastAPI dependency — only stdlib + sqlite3.  Split from screen_hug_review.py
(which imports FastAPI) so the business logic can be unit-tested without the
HTTP framework (same pattern as screen_hug_mint_html.py / screen_hug_review_html.py).

Exported:
  load_queue(conn)                          -> list[dict] of needs_review rows
  fetch_link(conn, token, phone)            -> dict | None
  set_status(conn, token, phone, status)    -> None
  confirm_link(conn, token, phone, resolved_customer_id, phone_to_attach) -> None
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def load_queue(conn: sqlite3.Connection) -> list[dict]:
    """Return all needs_review rows, newest first, enriched with party names."""
    rows = conn.execute(
        """
        SELECT
            il.token,
            il.buyer_customer_id,
            il.scanner_phone,
            il.scanner_zalo_uid,
            il.resolved_customer_id,
            il.confidence,
            il.status,
            il.ts,
            buyer.display_name   AS buyer_name,
            scanner.display_name AS scanner_name
        FROM crm_identity_link il
        LEFT JOIN crm_party buyer   ON buyer.party_id   = il.buyer_customer_id
        LEFT JOIN crm_party scanner ON scanner.party_id = il.resolved_customer_id
        WHERE il.status = 'needs_review'
        ORDER BY il.ts DESC
        """,
        [],
    ).fetchall()
    return [dict(r) for r in rows]


def fetch_link(
    conn: sqlite3.Connection, token: str, phone: str | None
) -> dict | None:
    """Fetch a single crm_identity_link row by UNIQUE (token, scanner_phone)."""
    if phone is None:
        row = conn.execute(
            "SELECT * FROM crm_identity_link WHERE token = ? AND scanner_phone IS NULL",
            (token,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM crm_identity_link WHERE token = ? AND scanner_phone = ?",
            (token, phone),
        ).fetchone()
    return dict(row) if row else None


def set_status(
    conn: sqlite3.Connection, token: str, phone: str | None, status: str
) -> None:
    """Update status (and ts) for a single row keyed by (token, scanner_phone)."""
    now = _utc_now()
    if phone is None:
        conn.execute(
            "UPDATE crm_identity_link SET status = ?, ts = ?"
            " WHERE token = ? AND scanner_phone IS NULL",
            (status, now, token),
        )
    else:
        conn.execute(
            "UPDATE crm_identity_link SET status = ?, ts = ?"
            " WHERE token = ? AND scanner_phone = ?",
            (status, now, token, phone),
        )
    conn.commit()


def confirm_link(
    conn: sqlite3.Connection,
    token: str,
    phone: str | None,
    resolved_customer_id: str,
    phone_to_attach: str | None,
) -> None:
    """Set status='linked' and apply the phone identity to the chosen party.

    Identity insertion uses INSERT OR IGNORE (never overwrites an existing row).
    contact_quality is set to 'unverified': the scanner provided their phone
    voluntarily, equivalent to the C2/C3 capture path — phone captured but not
    OTP-confirmed.  The contactability ladder is respected: only 'masked' and
    'zalo_follower' are promoted; 'unverified' and 'verified' are left alone.
    """
    now = _utc_now()

    # 1. Promote the link row to 'linked', and update resolved_customer_id in
    #    case the CS agent chose a different party via override.
    if phone is None:
        conn.execute(
            "UPDATE crm_identity_link"
            " SET status = 'linked', resolved_customer_id = ?, ts = ?"
            " WHERE token = ? AND scanner_phone IS NULL",
            (resolved_customer_id, now, token),
        )
    else:
        conn.execute(
            "UPDATE crm_identity_link"
            " SET status = 'linked', resolved_customer_id = ?, ts = ?"
            " WHERE token = ? AND scanner_phone = ?",
            (resolved_customer_id, now, token, phone),
        )

    # 2. Attach phone identity if available (INSERT OR IGNORE — never overwrites).
    if phone_to_attach:
        identity_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT OR IGNORE INTO crm_party_identity
              (identity_id, party_id, source_system, identity_type, identity_value,
               confidence, is_primary, source_contact_quality, contact_quality, created_at)
            VALUES (?, ?, 'hug', 'phone', ?, 0.8, 0, 'unverified', 'unverified', ?)
            """,
            (identity_id, resolved_customer_id, phone_to_attach, now),
        )

        # 3. Promote contact_quality on the party's sapo_customer identity when
        #    the existing level is below 'unverified' on the contactability ladder.
        #    The ladder (ascending): masked < zalo_follower < unverified < verified.
        #    Only upward moves are applied — never downgrade.
        conn.execute(
            """
            UPDATE crm_party_identity
            SET contact_quality = 'unverified'
            WHERE party_id = ?
              AND identity_type = 'sapo_customer'
              AND contact_quality IN ('masked', 'zalo_follower')
            """,
            (resolved_customer_id,),
        )

    conn.commit()


def _utc_now() -> str:
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"
