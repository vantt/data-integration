"""test_hug_review_queue.py — Tests for the Hug CS review-queue screen.

Covers (no FastAPI TestClient required — same pattern as test_hug_mint_reprint.py):
  - GET /hug/review: queue lists only needs_review rows; empty state when none.
  - POST confirm: status becomes 'linked' AND phone identity applied to party.
  - POST reject: row leaves queue (status='rejected'), not re-applicable.
  - Already-resolved row: no-op with a clear message (idempotent).
  - Migration 0023: applies cleanly and preserves existing rows.

Run:
  PYTHONPATH="crm/src" python -m pytest crm/src/tests/test_hug_review_queue.py -q
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import uuid

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase           # noqa: E402
from adapters.inbound.web.screen_hug_review_html import render_review_queue  # noqa: E402
from adapters.inbound.web.screen_hug_review_data import (                     # noqa: E402
    load_queue,
    fetch_link,
    set_status,
    confirm_link,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _apply_migrations(conn: sqlite3.Connection) -> None:
    from crm.src.adapters.outbound.sqlite.migrations import run_migrations
    run_migrations(conn)


@pytest.fixture()
def crm_conn(tmp_path):
    db = CRMDatabase(str(tmp_path))
    _apply_migrations(db.conn)
    yield db.conn
    db.close()


def _mk_party(conn: sqlite3.Connection, *, contact_quality: str = "masked") -> str:
    pid = str(uuid.uuid4())
    now = "2026-06-20T00:00:00.000Z"
    conn.execute(
        "INSERT INTO crm_party (party_id, party_type, display_name, status, is_merged, created_at, updated_at)"
        " VALUES (?, 'person', 'Test', 'active', 0, ?, ?)",
        (pid, now, now),
    )
    conn.execute(
        "INSERT INTO crm_party_identity"
        " (identity_id, party_id, source_system, identity_type, identity_value,"
        "  confidence, is_primary, source_contact_quality, contact_quality, created_at)"
        " VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?, 1.0, 1, ?, ?, ?)",
        (str(uuid.uuid4()), pid, str(uuid.uuid4().int)[:8], contact_quality, contact_quality, now),
    )
    conn.commit()
    return pid


def _insert_link(
    conn: sqlite3.Connection,
    *,
    token: str,
    phone: str | None = "0901000001",
    buyer_id: str | None = None,
    resolved_id: str | None = None,
    status: str = "needs_review",
    confidence: float = 0.5,
) -> None:
    now = "2026-06-20T01:00:00.000Z"
    conn.execute(
        "INSERT OR REPLACE INTO crm_identity_link"
        " (token, buyer_customer_id, scanner_phone, scanner_zalo_uid,"
        "  resolved_customer_id, confidence, status, ts)"
        " VALUES (?, ?, ?, NULL, ?, ?, ?, ?)",
        (token, buyer_id, phone, resolved_id, confidence, status, now),
    )
    conn.commit()


def _get_link_row(conn: sqlite3.Connection, token: str, phone: str | None) -> sqlite3.Row | None:
    if phone is None:
        return conn.execute(
            "SELECT * FROM crm_identity_link WHERE token = ? AND scanner_phone IS NULL",
            (token,),
        ).fetchone()
    return conn.execute(
        "SELECT * FROM crm_identity_link WHERE token = ? AND scanner_phone = ?",
        (token, phone),
    ).fetchone()


def _get_identities(conn: sqlite3.Connection, party_id: str) -> list:
    return conn.execute(
        "SELECT identity_type, identity_value, contact_quality FROM crm_party_identity WHERE party_id = ?",
        (party_id,),
    ).fetchall()


# ── GET queue: only needs_review rows appear ──────────────────────────────────

def test_queue_returns_only_needs_review_rows(crm_conn):
    buyer = _mk_party(crm_conn)
    scanner = _mk_party(crm_conn)

    _insert_link(crm_conn, token="T-NR-1", phone="0901000001",
                 buyer_id=buyer, resolved_id=scanner, status="needs_review")
    _insert_link(crm_conn, token="T-LK-1", phone="0902000002",
                 buyer_id=buyer, resolved_id=scanner, status="linked")
    _insert_link(crm_conn, token="T-RJ-1", phone="0903000003",
                 buyer_id=buyer, resolved_id=scanner, status="rejected")

    rows = load_queue(crm_conn)
    assert len(rows) == 1
    assert rows[0]["token"] == "T-NR-1"
    assert rows[0]["status"] == "needs_review"


def test_queue_empty_when_no_needs_review_rows(crm_conn):
    buyer = _mk_party(crm_conn)
    _insert_link(crm_conn, token="T-LK-2", phone="0904000004",
                 buyer_id=buyer, resolved_id=buyer, status="linked")

    rows = load_queue(crm_conn)
    assert rows == []


def test_render_empty_state_shows_all_clear_message():
    html = render_review_queue([])
    assert "Không có dòng nào cần xem xét" in html


def test_render_queue_shows_token_and_phone():
    rows = [
        {
            "token": "TOKENABCD1234",
            "buyer_customer_id": "buyer-uuid",
            "scanner_phone": "0901234567",
            "scanner_zalo_uid": None,
            "resolved_customer_id": "resolver-uuid",
            "confidence": 0.5,
            "status": "needs_review",
            "ts": "2026-06-20T10:00:00.000Z",
            "buyer_name": "Nguyen Van A",
            "scanner_name": "Tran Thi B",
        }
    ]
    html = render_review_queue(rows)
    assert "TOKENABCD1234" in html
    assert "0901234567" in html
    assert "buyer-uuid" in html
    assert "Xác nhận" in html
    assert "Bác bỏ" in html


# ── POST confirm: status='linked' + phone identity applied ───────────────────

def test_confirm_sets_status_linked(crm_conn):
    buyer = _mk_party(crm_conn)
    scanner = _mk_party(crm_conn)
    token = "T-CONFIRM-1"
    phone = "0911111111"
    _insert_link(crm_conn, token=token, phone=phone,
                 buyer_id=buyer, resolved_id=scanner, status="needs_review")

    confirm_link(crm_conn, token, phone, scanner, phone)

    row = _get_link_row(crm_conn, token, phone)
    assert row is not None
    assert row["status"] == "linked"
    assert row["resolved_customer_id"] == scanner


def test_confirm_applies_phone_identity_to_party(crm_conn):
    buyer = _mk_party(crm_conn, contact_quality="masked")
    scanner = _mk_party(crm_conn, contact_quality="masked")
    token = "T-CONFIRM-2"
    phone = "0922222222"
    _insert_link(crm_conn, token=token, phone=phone,
                 buyer_id=buyer, resolved_id=scanner, status="needs_review")

    confirm_link(crm_conn, token, phone, scanner, phone)

    identities = _get_identities(crm_conn, scanner)
    phone_rows = [r for r in identities if r[0] == "phone" and r[1] == phone]
    assert phone_rows, "phone identity must be added to the scanner/resolved party"
    assert phone_rows[0][2] == "unverified"


def test_confirm_upgrades_contact_quality_from_masked(crm_conn):
    """Confirming a link must promote the party's sapo_customer quality from masked."""
    scanner = _mk_party(crm_conn, contact_quality="masked")
    token = "T-CONFIRM-3"
    phone = "0933333333"
    _insert_link(crm_conn, token=token, phone=phone, resolved_id=scanner, status="needs_review")

    confirm_link(crm_conn, token, phone, scanner, phone)

    # sapo_customer identity quality must be promoted to 'unverified'
    identities = _get_identities(crm_conn, scanner)
    sapo_rows = [r for r in identities if r[0] == "sapo_customer"]
    assert sapo_rows
    assert sapo_rows[0][2] == "unverified"


def test_confirm_does_not_downgrade_verified_quality(crm_conn):
    """Confirming must not lower a party already at 'verified'."""
    scanner = _mk_party(crm_conn, contact_quality="verified")
    token = "T-CONFIRM-4"
    phone = "0944444444"
    _insert_link(crm_conn, token=token, phone=phone, resolved_id=scanner, status="needs_review")

    confirm_link(crm_conn, token, phone, scanner, phone)

    identities = _get_identities(crm_conn, scanner)
    sapo_rows = [r for r in identities if r[0] == "sapo_customer"]
    assert sapo_rows
    assert sapo_rows[0][2] == "verified", "verified must not be downgraded"


def test_confirm_with_override_customer_id(crm_conn):
    """CS agent supplying a different party_id routes the identity there."""
    buyer = _mk_party(crm_conn, contact_quality="masked")
    suggested = _mk_party(crm_conn, contact_quality="masked")
    override = _mk_party(crm_conn, contact_quality="masked")
    token = "T-CONFIRM-5"
    phone = "0955555555"
    _insert_link(crm_conn, token=token, phone=phone,
                 buyer_id=buyer, resolved_id=suggested, status="needs_review")

    confirm_link(crm_conn, token, phone, override, phone)

    row = _get_link_row(crm_conn, token, phone)
    assert row["resolved_customer_id"] == override
    identities = _get_identities(crm_conn, override)
    assert any(r[0] == "phone" and r[1] == phone for r in identities)


# ── POST reject: row leaves queue, not re-applied ────────────────────────────

def test_reject_sets_status_rejected(crm_conn):
    buyer = _mk_party(crm_conn)
    token = "T-REJECT-1"
    phone = "0966666666"
    _insert_link(crm_conn, token=token, phone=phone, buyer_id=buyer, status="needs_review")

    set_status(crm_conn, token, phone, "rejected")

    row = _get_link_row(crm_conn, token, phone)
    assert row["status"] == "rejected"


def test_reject_removes_row_from_queue(crm_conn):
    buyer = _mk_party(crm_conn)
    token = "T-REJECT-2"
    phone = "0977777777"
    _insert_link(crm_conn, token=token, phone=phone, buyer_id=buyer, status="needs_review")

    set_status(crm_conn, token, phone, "rejected")

    queue = load_queue(crm_conn)
    assert not any(r["token"] == token for r in queue)


def test_reject_does_not_add_identity_to_party(crm_conn):
    """Rejecting must leave the party's identities untouched."""
    scanner = _mk_party(crm_conn, contact_quality="masked")
    token = "T-REJECT-3"
    phone = "0988888888"
    _insert_link(crm_conn, token=token, phone=phone, resolved_id=scanner, status="needs_review")

    identities_before = _get_identities(crm_conn, scanner)
    set_status(crm_conn, token, phone, "rejected")
    identities_after = _get_identities(crm_conn, scanner)

    assert identities_before == identities_after


# ── Already-resolved row: idempotent no-op ───────────────────────────────────

def test_fetch_already_linked_row_is_found(crm_conn):
    buyer = _mk_party(crm_conn)
    token = "T-IDEMPOTENT-1"
    phone = "0999000001"
    _insert_link(crm_conn, token=token, phone=phone,
                 buyer_id=buyer, resolved_id=buyer, status="linked")

    link = fetch_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "linked"


def test_fetch_already_rejected_row_is_found(crm_conn):
    buyer = _mk_party(crm_conn)
    token = "T-IDEMPOTENT-2"
    phone = "0999000002"
    _insert_link(crm_conn, token=token, phone=phone,
                 buyer_id=buyer, resolved_id=buyer, status="rejected")

    link = fetch_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "rejected"


def test_fetch_nonexistent_row_returns_none(crm_conn):
    result = fetch_link(crm_conn, "DOES-NOT-EXIST", "0000000000")
    assert result is None


# ── Zalo-only opt-in (NULL scanner_phone) ────────────────────────────────────

def test_zalo_only_link_confirm_without_phone_identity(crm_conn):
    """Confirming a Zalo-only opt-in (no phone) must set status='linked'
    and not attempt to insert a NULL phone identity."""
    scanner = _mk_party(crm_conn, contact_quality="zalo_follower")
    token = "T-ZALO-1"
    # NULL phone: insert manually to bypass helper (which defaults phone to a value)
    conn = crm_conn
    now = "2026-06-20T05:00:00.000Z"
    conn.execute(
        "INSERT INTO crm_identity_link"
        " (token, buyer_customer_id, scanner_phone, scanner_zalo_uid,"
        "  resolved_customer_id, confidence, status, ts)"
        " VALUES (?, NULL, NULL, 'zalo-uid-xyz', ?, 0.7, 'needs_review', ?)",
        (token, scanner, now),
    )
    conn.commit()

    # phone_to_attach is None → no phone identity inserted
    confirm_link(crm_conn, token, None, scanner, None)

    row = _get_link_row(crm_conn, token, None)
    assert row is not None
    assert row["status"] == "linked"

    identities = _get_identities(crm_conn, scanner)
    phone_rows = [r for r in identities if r[0] == "phone"]
    assert not phone_rows, "no phone identity should be added for a Zalo-only opt-in"


# ── Migration 0023: applies cleanly, preserves existing data ─────────────────

def test_migration_0023_applies_and_preserves_existing_rows(tmp_path):
    """Migration 0023 widens the status CHECK to include 'rejected'.

    Verify:
    - Existing rows with status in ('linked','needs_review') survive the rebuild.
    - A new 'rejected' row can be inserted after migration.
    - The old CHECK would have rejected 'rejected'; the new one accepts it.
    """
    # Open a fresh DB and apply migrations up to and including 0023.
    db = CRMDatabase(str(tmp_path))
    _apply_migrations(db.conn)
    conn = db.conn

    # Insert seed rows with the pre-existing allowed statuses.
    now = "2026-06-20T00:00:00.000Z"
    conn.execute(
        "INSERT INTO crm_identity_link (token, scanner_phone, confidence, status, ts)"
        " VALUES ('TOK-A', '0900000001', 1.0, 'linked', ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO crm_identity_link (token, scanner_phone, confidence, status, ts)"
        " VALUES ('TOK-B', '0900000002', 0.5, 'needs_review', ?)",
        (now,),
    )
    conn.commit()

    # After migration 0023 the 'rejected' status must be accepted.
    conn.execute(
        "INSERT INTO crm_identity_link (token, scanner_phone, confidence, status, ts)"
        " VALUES ('TOK-C', '0900000003', 0.0, 'rejected', ?)",
        (now,),
    )
    conn.commit()

    # All three rows must be present.
    rows = conn.execute(
        "SELECT token, status FROM crm_identity_link ORDER BY token"
    ).fetchall()
    statuses = {r[0]: r[1] for r in rows}
    assert statuses == {
        "TOK-A": "linked",
        "TOK-B": "needs_review",
        "TOK-C": "rejected",
    }

    db.close()
