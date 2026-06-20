"""test_hug_identity_resolver.py — Unit tests for the §8 identity-bridge policy.

One test per policy row in the §8 table, plus:
  - idempotent re-opt-in (C7)
  - conflict → needs_review (C3 cross-signal)
  - happy-path unclaimed → masked buyer assign (C2)
  - contactability ladder never-downgrade

All tests use temp SQLite (crm.db + hug.db) fixtures and inject opt-in rows
directly via the optin_rows seam — no live olap.duckdb is needed.

Run: PYTHONPATH="crm/src" python -m pytest crm/src/tests/ -q
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

from crm.src.adapters.outbound.sqlite.connection import CRMDatabase  # noqa: E402
from hug import db as hug_db                                          # noqa: E402
from hug.identity_resolver import resolve_new_optins                  # noqa: E402
from hug.identity_resolver_io import ladder_rank as _ladder_rank      # noqa: E402
from hug.identity_resolver_io import upgrade_quality as _upgrade_quality  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers: bootstrap test databases
# ---------------------------------------------------------------------------

def _apply_crm_migrations(crm_conn: sqlite3.Connection) -> None:
    """Apply all CRM migrations including 0022_hug_identity_link."""
    from crm.src.adapters.outbound.sqlite.migrations import run_migrations
    run_migrations(crm_conn)


def _mk_party(crm_conn: sqlite3.Connection, *, contact_quality: str = "masked") -> str:
    """Insert a minimal crm_party + sapo_customer identity; return party_id."""
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4().int)[:10]  # fake sapo customer id
    now = "2026-06-20T00:00:00.000Z"
    crm_conn.execute(
        "INSERT INTO crm_party (party_id, party_type, display_name, status, is_merged, created_at, updated_at)"
        " VALUES (?, 'person', 'Test Party', 'active', 0, ?, ?)",
        (pid, now, now),
    )
    iid = str(uuid.uuid4())
    crm_conn.execute(
        "INSERT INTO crm_party_identity"
        " (identity_id, party_id, source_system, identity_type, identity_value,"
        "  confidence, is_primary, source_contact_quality, contact_quality, created_at)"
        " VALUES (?, ?, 'sapo_v2', 'sapo_customer', ?, 1.0, 1, ?, ?, ?)",
        (iid, pid, cid, contact_quality, contact_quality, now),
    )
    crm_conn.commit()
    return pid, cid


def _add_phone_identity_for_party(
    crm_conn: sqlite3.Connection,
    party_id: str,
    phone: str,
    quality: str = "unverified",
) -> None:
    """Attach a phone identity directly to a party (test setup)."""
    now = "2026-06-20T00:00:00.000Z"
    crm_conn.execute(
        "INSERT OR IGNORE INTO crm_party_identity"
        " (identity_id, party_id, source_system, identity_type, identity_value,"
        "  confidence, is_primary, source_contact_quality, contact_quality, created_at)"
        " VALUES (?, ?, 'sapo_v2', 'phone', ?, 1.0, 0, ?, ?, ?)",
        (str(uuid.uuid4()), party_id, phone, quality, quality, now),
    )
    crm_conn.commit()


def _bind_token(hug_conn: sqlite3.Connection, token: str, *, order_code: str, is_gift: bool = False) -> None:
    """Insert a bound hug_token row for a given token."""
    now = "2026-06-20T00:00:00.000Z"
    hug_conn.execute(
        "INSERT OR REPLACE INTO hug_token"
        " (token, op_type, order_code, is_gift, status, batch_id, created_at)"
        " VALUES (?, 'package_insert', ?, ?, 'bound', 'B-test', ?)",
        (token, order_code, 1 if is_gift else 0, now),
    )
    hug_conn.commit()


def _optin(token: str, phone: str = "", zalo_uid: str = "", buyer_cid: str = "") -> dict:
    return {
        "token": token,
        "buyer_customer_id": buyer_cid or None,
        "phone": phone or None,
        "zalo_uid": zalo_uid or None,
        "name": None,
        "consent_json": None,
        "event_ts": "2026-06-20T01:00:00Z",
    }


def _get_link(crm_conn: sqlite3.Connection, token: str, phone: str | None):
    """Fetch the crm_identity_link row for (token, phone)."""
    return crm_conn.execute(
        "SELECT * FROM crm_identity_link WHERE token = ? AND scanner_phone IS ?",
        (token, phone),
    ).fetchone()


def _get_identities(crm_conn: sqlite3.Connection, party_id: str) -> list:
    return crm_conn.execute(
        "SELECT identity_type, identity_value, contact_quality FROM crm_party_identity WHERE party_id = ?",
        (party_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def dbs(tmp_path):
    """Yield (crm_conn, hug_conn, watermark_path) with migrations applied."""
    data_dir = str(tmp_path)
    crm_db = CRMDatabase(data_dir)
    _apply_crm_migrations(crm_db.conn)
    hug_conn = hug_db.connect(str(tmp_path / "hug.db"))
    wm = str(tmp_path / "watermark.json")
    yield crm_db.conn, hug_conn, wm
    hug_conn.close()
    crm_db.close()


# ---------------------------------------------------------------------------
# Ladder utilities
# ---------------------------------------------------------------------------

def test_ladder_rank_ordering():
    assert _ladder_rank("masked") < _ladder_rank("zalo_follower")
    assert _ladder_rank("zalo_follower") < _ladder_rank("unverified")
    assert _ladder_rank("unverified") < _ladder_rank("verified")


def test_upgrade_quality_never_downgrades():
    assert _upgrade_quality("verified", "masked") == "verified"
    assert _upgrade_quality("unverified", "zalo_follower") == "unverified"
    assert _upgrade_quality("masked", "unverified") == "unverified"


# ---------------------------------------------------------------------------
# C1: phone matches buyer's own identity → phone_verified; linked
# ---------------------------------------------------------------------------

def test_c1_phone_matches_buyers_own_identity_sets_verified_and_linked(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="unverified")
    phone = "0901000001"
    _add_phone_identity_for_party(crm_conn, party_id, phone, quality="unverified")

    token = "TOKEN-C1-001"
    _bind_token(hug_conn, token, order_code="SO-001")

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=cid)],
    )

    link = _get_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "linked"
    assert link["resolved_customer_id"] == party_id
    assert link["confidence"] == 1.0

    # contact_quality must have been upgraded to verified
    identities = _get_identities(crm_conn, party_id)
    qualities = {r[2] for r in identities}
    assert "verified" in qualities


# ---------------------------------------------------------------------------
# C2: phone unclaimed + buyer masked → assign; phone_unverified; linked
# ---------------------------------------------------------------------------

def test_c2_unclaimed_phone_assigned_to_masked_buyer(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="masked")
    phone = "0912345678"

    token = "TOKEN-C2-001"
    _bind_token(hug_conn, token, order_code="SO-002")

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=cid)],
    )

    link = _get_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "linked"
    assert link["resolved_customer_id"] == party_id
    assert link["confidence"] == 1.0

    # Phone identity must now exist on the buyer's party
    identities = _get_identities(crm_conn, party_id)
    phone_rows = [r for r in identities if r[0] == "phone" and r[1] == phone]
    assert phone_rows, "phone identity must be added to buyer party"
    assert phone_rows[0][2] == "unverified"


# ---------------------------------------------------------------------------
# C3: phone belongs to different customer → route to that party; needs_review
# ---------------------------------------------------------------------------

def test_c3_phone_belongs_to_different_party_needs_review(dbs):
    crm_conn, hug_conn, wm = dbs
    # Buyer party (masked)
    buyer_party_id, buyer_cid = _mk_party(crm_conn, contact_quality="masked")
    # Different party that already owns the phone
    other_party_id, _ = _mk_party(crm_conn, contact_quality="unverified")
    phone = "0933000111"
    _add_phone_identity_for_party(crm_conn, other_party_id, phone, quality="unverified")

    token = "TOKEN-C3-001"
    _bind_token(hug_conn, token, order_code="SO-003")

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=buyer_cid)],
    )

    link = _get_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "needs_review"
    # Must resolve to the phone owner (C), not the buyer (A)
    assert link["resolved_customer_id"] == other_party_id
    assert link["confidence"] == 0.5
    # Buyer party MUST NOT have the phone attached
    buyer_identities = _get_identities(crm_conn, buyer_party_id)
    buyer_phones = [r for r in buyer_identities if r[0] == "phone"]
    assert not buyer_phones, "phone must not be assigned to buyer when owned by another party"


# ---------------------------------------------------------------------------
# C4: is_gift → opt-in routes to scanner (phone owner), not buyer
# ---------------------------------------------------------------------------

def test_c4_gift_optins_route_to_scanner_not_buyer(dbs):
    crm_conn, hug_conn, wm = dbs
    buyer_party_id, buyer_cid = _mk_party(crm_conn, contact_quality="masked")
    scanner_party_id, _ = _mk_party(crm_conn, contact_quality="unverified")
    phone = "0944000222"
    _add_phone_identity_for_party(crm_conn, scanner_party_id, phone, quality="unverified")

    token = "TOKEN-C4-001"
    _bind_token(hug_conn, token, order_code="SO-004", is_gift=True)

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=buyer_cid)],
    )

    link = _get_link(crm_conn, token, phone)
    assert link is not None
    # Resolves to scanner (phone owner), NOT the buyer
    assert link["resolved_customer_id"] == scanner_party_id
    # Buyer party unchanged (§8 "do NOT touch buyer A")
    buyer_identities = _get_identities(crm_conn, buyer_party_id)
    buyer_phones = [r for r in buyer_identities if r[0] == "phone"]
    assert not buyer_phones


# ---------------------------------------------------------------------------
# C5: Zalo follow only, no phone → zalo_follower; linked
# ---------------------------------------------------------------------------

def test_c5_zalo_only_sets_zalo_follower_on_masked_buyer(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="masked")

    token = "TOKEN-C5-001"
    _bind_token(hug_conn, token, order_code="SO-005")

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone="", zalo_uid="zalo-uid-abc", buyer_cid=cid)],
    )

    link = _get_link(crm_conn, token, None)  # phone is NULL
    assert link is not None
    assert link["status"] == "linked"
    assert link["scanner_zalo_uid"] == "zalo-uid-abc"

    # contact_quality must have been upgraded to zalo_follower (from masked)
    identities = _get_identities(crm_conn, party_id)
    qualities = {r[2] for r in identities}
    assert "zalo_follower" in qualities


def test_c5_zalo_only_does_not_downgrade_existing_unverified(dbs):
    """Zalo follow must NOT downgrade a buyer who already has unverified phone."""
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="unverified")
    _add_phone_identity_for_party(crm_conn, party_id, "0900000001", quality="unverified")

    token = "TOKEN-C5-002"
    _bind_token(hug_conn, token, order_code="SO-005b")

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone="", zalo_uid="zalo-uid-xyz", buyer_cid=cid)],
    )

    # contact_quality must still be at least unverified — not downgraded to zalo_follower
    identities = _get_identities(crm_conn, party_id)
    qualities = {r[2] for r in identities}
    assert "unverified" in qualities
    assert "masked" not in qualities


# ---------------------------------------------------------------------------
# C6: multiple/changed phones → ADD identity, never delete
# ---------------------------------------------------------------------------

def test_c6_adding_new_phone_does_not_remove_existing_phones(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="unverified")
    existing_phone = "0900000001"
    _add_phone_identity_for_party(crm_conn, party_id, existing_phone, quality="unverified")

    token = "TOKEN-C6-001"
    _bind_token(hug_conn, token, order_code="SO-006")
    new_phone = "0911000002"

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=new_phone, buyer_cid=cid)],
    )

    identities = _get_identities(crm_conn, party_id)
    phone_values = {r[1] for r in identities if r[0] == "phone"}
    assert existing_phone in phone_values, "existing phone must still be present"
    assert new_phone in phone_values, "new phone must be added"


# ---------------------------------------------------------------------------
# C7: re-opt-in (same token + phone) → idempotent, update existing row
# ---------------------------------------------------------------------------

def test_c7_re_optin_is_idempotent(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="masked")
    phone = "0922000333"

    token = "TOKEN-C7-001"
    _bind_token(hug_conn, token, order_code="SO-007")

    row = _optin(token, phone=phone, buyer_cid=cid)

    # First opt-in
    resolve_new_optins(crm_conn, hug_conn, "", wm, optin_rows=[row])
    # Second opt-in with a newer ts (watermark must allow through)
    row2 = dict(row, event_ts="2026-06-20T02:00:00Z")
    resolve_new_optins(crm_conn, hug_conn, "", wm, optin_rows=[row2])

    # Only one crm_identity_link row must exist
    count = crm_conn.execute(
        "SELECT COUNT(*) FROM crm_identity_link WHERE token = ? AND scanner_phone = ?",
        (token, phone),
    ).fetchone()[0]
    assert count == 1, "re-opt-in must update the existing row, not insert a duplicate"


# ---------------------------------------------------------------------------
# Conflict → needs_review (cross-signal: is_gift + phone owner differs from buyer)
# ---------------------------------------------------------------------------

def test_gift_plus_phone_owner_differs_from_buyer_is_needs_review(dbs):
    crm_conn, hug_conn, wm = dbs
    buyer_party_id, buyer_cid = _mk_party(crm_conn, contact_quality="masked")
    scanner_party_id, _ = _mk_party(crm_conn, contact_quality="unverified")
    phone = "0955000444"
    _add_phone_identity_for_party(crm_conn, scanner_party_id, phone)

    token = "TOKEN-GIFT-CONFLICT"
    _bind_token(hug_conn, token, order_code="SO-008", is_gift=True)

    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=buyer_cid)],
    )

    link = _get_link(crm_conn, token, phone)
    assert link is not None
    assert link["status"] == "needs_review"
    assert link["resolved_customer_id"] == scanner_party_id


# ---------------------------------------------------------------------------
# Ladder: never downgrade contact_quality
# ---------------------------------------------------------------------------

def test_ladder_never_downgrade_verified_to_unverified(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="verified")
    phone = "0966000555"
    _add_phone_identity_for_party(crm_conn, party_id, phone, quality="verified")

    token = "TOKEN-LADDER-001"
    _bind_token(hug_conn, token, order_code="SO-009")

    # Opt-in with the buyer's own phone — C1 path applies phone_verified upgrade
    # but since it's already verified, quality must stay at verified not drop
    resolve_new_optins(
        crm_conn, hug_conn, "", wm,
        optin_rows=[_optin(token, phone=phone, buyer_cid=cid)],
    )

    identities = _get_identities(crm_conn, party_id)
    phone_rows = [r for r in identities if r[0] == "phone" and r[1] == phone]
    assert phone_rows
    assert phone_rows[0][2] == "verified", "verified must not be downgraded"


# ---------------------------------------------------------------------------
# Watermark: only processes rows newer than last watermark
# ---------------------------------------------------------------------------

def test_watermark_skips_already_processed_rows(dbs):
    crm_conn, hug_conn, wm = dbs
    party_id, cid = _mk_party(crm_conn, contact_quality="masked")
    phone = "0977000666"

    token = "TOKEN-WM-001"
    _bind_token(hug_conn, token, order_code="SO-010")

    row = _optin(token, phone=phone, buyer_cid=cid)

    # First run — should process the row and write the link
    n = resolve_new_optins(crm_conn, hug_conn, "", wm, optin_rows=[row])
    assert n == 1

    # Second run with the same row — watermark should block it (row ts is not newer)
    n2 = resolve_new_optins(crm_conn, hug_conn, "", wm, optin_rows=[row])
    assert n2 == 0

    count = crm_conn.execute(
        "SELECT COUNT(*) FROM crm_identity_link WHERE token = ?", (token,)
    ).fetchone()[0]
    assert count == 1
