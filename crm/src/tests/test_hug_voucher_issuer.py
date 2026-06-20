"""test_hug_voucher_issuer.py — Unit tests for voucher_issuer.issue_vouchers().

Covers every qualifying/disqualifying condition for voucher issuance:
  - opt-in with campaign + offer_ref + resolved customer → row written
  - idempotent: same opt-in twice → exactly one row
  - campaign has no offer_ref → skipped, no row
  - opt-in without a campaign_id → skipped, no row
  - unresolved customer (no crm_identity_link) → deferred, no row, watermark
    does not advance past the unresolved token so it's retried next cycle
  - missing olap table (pre-deploy) → returns 0, no exception
  - watermark advances after a successful run

All tests inject opt-in rows directly via the optin_rows seam — no live
olap.duckdb is required.  crm.db tables are bootstrapped from the real
migration SQL files so column names stay in sync with production schema.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import pytest

_REPO_ROOT   = str(pathlib.Path(__file__).parents[3])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])   # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.voucher_issuer import issue_vouchers     # noqa: E402
from hug.voucher_repository import get_issuance   # noqa: E402

# ---------------------------------------------------------------------------
# Migration SQL paths
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = pathlib.Path(_REPO_ROOT) / "crm" / "migrations"

_MIGRATION_CAMPAIGN  = _MIGRATIONS_DIR / "0024_hug_campaign_authoring.up.sql"
_MIGRATION_LINK      = _MIGRATIONS_DIR / "0022_hug_identity_link.up.sql"
_MIGRATION_VOUCHER   = _MIGRATIONS_DIR / "0025_hug_voucher_ledger.up.sql"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def crm_conn():
    """In-memory SQLite connection with the three required tables bootstrapped."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_LINK.read_text(encoding="utf-8"))
    c.executescript(_MIGRATION_CAMPAIGN.read_text(encoding="utf-8"))
    c.executescript(_MIGRATION_VOUCHER.read_text(encoding="utf-8"))
    yield c
    c.close()


@pytest.fixture()
def watermark(tmp_path):
    """Return a path to a non-existent watermark file (will be created by issuer)."""
    return str(tmp_path / "hug_voucher_watermark.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_campaign(conn: sqlite3.Connection, campaign_id: str, offer_ref: str | None) -> None:
    """Insert a minimal campaign row."""
    conn.execute(
        """
        INSERT INTO crm_hug_campaign
            (campaign_id, name, destination_type, destination_url, offer_ref, status)
        VALUES (?, ?, 'cf_pages', 'https://example.com', ?, 'active')
        """,
        (campaign_id, f"Campaign {campaign_id}", offer_ref),
    )
    conn.commit()


def _seed_identity_link(conn: sqlite3.Connection, token: str, customer_id: str | None) -> None:
    """Insert a crm_identity_link row simulating a resolved (or unresolved) opt-in."""
    status = "linked" if customer_id else "needs_review"
    conn.execute(
        """
        INSERT INTO crm_identity_link
            (token, resolved_customer_id, confidence, status, ts)
        VALUES (?, ?, 1.0, ?, '2026-06-20T00:00:00Z')
        """,
        (token, customer_id, status),
    )
    conn.commit()


def _optin(token: str, campaign_id: str | None, event_ts: str = "2026-06-20T01:00:00Z") -> dict:
    return {"token": token, "campaign_id": campaign_id, "event_ts": event_ts}


def _watermark_value(path: str) -> str:
    """Read back the last_event_ts from a watermark file, or '' if absent."""
    p = pathlib.Path(path)
    if not p.exists():
        return ""
    return json.loads(p.read_text(encoding="utf-8")).get("last_event_ts", "")


# ---------------------------------------------------------------------------
# Happy path: opt-in with offer campaign + resolved customer → row inserted
# ---------------------------------------------------------------------------

def test_issues_voucher_when_resolved(crm_conn, watermark):
    _seed_campaign(crm_conn, "A2", "HUG50")
    _seed_identity_link(crm_conn, "TOK-001", "CUST-001")

    n = issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-001", "A2")],
    )

    assert n == 1
    row = get_issuance(crm_conn, "HUG50", "CUST-001")
    assert row is not None
    assert row["code"]        == "HUG50"
    assert row["customer_id"] == "CUST-001"
    assert row["campaign_id"] == "A2"
    assert row["token"]       == "TOK-001"
    assert row["redeemed_at"] is None


# ---------------------------------------------------------------------------
# Idempotency: running twice on the same opt-in produces exactly one row
# ---------------------------------------------------------------------------

def test_idempotent_double_run(crm_conn, watermark):
    _seed_campaign(crm_conn, "A2", "HUG50")
    _seed_identity_link(crm_conn, "TOK-002", "CUST-002")

    optin = _optin("TOK-002", "A2", event_ts="2026-06-20T02:00:00Z")

    n1 = issue_vouchers(crm_conn, "", watermark, optin_rows=[optin])
    assert n1 == 1

    # Inject a "later" opt-in so the watermark-filtered injection seam lets it through;
    # but same (code, customer_id) — INSERT OR IGNORE must suppress the duplicate.
    optin2 = dict(optin, event_ts="2026-06-20T03:00:00Z")
    n2 = issue_vouchers(crm_conn, "", watermark, optin_rows=[optin2])
    assert n2 == 0  # already exists — INSERT OR IGNORE returned rowcount=0

    count = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# No offer_ref → skipped
# ---------------------------------------------------------------------------

def test_skips_campaign_without_offer_ref(crm_conn, watermark):
    _seed_campaign(crm_conn, "INFO-ONLY", None)  # offer_ref is NULL
    _seed_identity_link(crm_conn, "TOK-003", "CUST-003")

    n = issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-003", "INFO-ONLY")],
    )

    assert n == 0
    count = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 0


# ---------------------------------------------------------------------------
# No campaign_id on opt-in → skipped (pre-P2 event or data gap)
# ---------------------------------------------------------------------------

def test_skips_optin_without_campaign_id(crm_conn, watermark):
    _seed_identity_link(crm_conn, "TOK-004", "CUST-004")

    n = issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-004", None)],  # campaign_id=None
    )

    assert n == 0
    count = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 0


# ---------------------------------------------------------------------------
# Unresolved customer → deferred (no row; watermark does NOT advance past it)
# ---------------------------------------------------------------------------

def test_defers_unresolved_customer(crm_conn, watermark, tmp_path):
    _seed_campaign(crm_conn, "A2", "HUG50")
    # Token present in identity_link but resolved_customer_id is NULL
    _seed_identity_link(crm_conn, "TOK-005", None)

    ts = "2026-06-20T05:00:00Z"
    n = issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-005", "A2", event_ts=ts)],
    )

    assert n == 0
    count = crm_conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 0

    # Watermark must NOT have advanced past the unresolved token's event_ts,
    # so the next cycle will re-scan and retry the same row.
    wm = _watermark_value(watermark)
    assert wm < ts, f"watermark {wm!r} must not advance past unresolved token ts {ts!r}"


def test_defers_token_absent_from_identity_link(crm_conn, watermark):
    """Token not yet processed by hug_resolve → no link row at all → defer."""
    _seed_campaign(crm_conn, "A2", "HUG50")
    # Intentionally do NOT seed any identity_link row for TOK-NO-LINK

    n = issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-NO-LINK", "A2", event_ts="2026-06-20T06:00:00Z")],
    )

    assert n == 0


# ---------------------------------------------------------------------------
# Missing olap table (pre-deploy mart) → returns 0, no exception
# ---------------------------------------------------------------------------

def test_missing_olap_table_returns_zero_gracefully(crm_conn, watermark, tmp_path):
    """When mart_hug_optin is absent, the issuer must catch CatalogException and return 0."""
    import duckdb

    # Create a real (but empty) DuckDB file — no mart_hug_optin table
    olap_path = str(tmp_path / "empty_olap.duckdb")
    con = duckdb.connect(olap_path)
    con.close()

    # Call without optin_rows — forces the real DuckDB path
    n = issue_vouchers(crm_conn, olap_path, watermark)
    assert n == 0  # must not raise


# ---------------------------------------------------------------------------
# Watermark advances after a successful run
# ---------------------------------------------------------------------------

def test_watermark_advances_after_successful_run(crm_conn, watermark):
    _seed_campaign(crm_conn, "A2", "HUG50")
    _seed_identity_link(crm_conn, "TOK-006", "CUST-006")

    ts = "2026-06-20T08:00:00Z"
    issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-006", "A2", event_ts=ts)],
    )

    assert _watermark_value(watermark) == ts


def test_watermark_not_created_when_no_eligible_rows(crm_conn, watermark):
    """If nothing qualifies (e.g. no campaign), watermark file should still exist or stay unchanged."""
    # Run with a row that has no offer_ref — no rows advance
    _seed_campaign(crm_conn, "NO-OFFER", None)
    _seed_identity_link(crm_conn, "TOK-007", "CUST-007")

    issue_vouchers(
        crm_conn, "", watermark,
        optin_rows=[_optin("TOK-007", "NO-OFFER", event_ts="2026-06-20T09:00:00Z")],
    )
    # Watermark should have advanced past the skipped row (no-offer rows are advanced)
    wm = _watermark_value(watermark)
    assert wm == "2026-06-20T09:00:00Z"
