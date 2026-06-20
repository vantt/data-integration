"""test_hug_voucher_redeem_matcher.py — Unit tests for voucher_redeem_matcher.

Tests cover:
  - Exact (customer_id, code) match → redeemed_at + order_code populated
  - No match when coupon code differs (wrong code)
  - No match when customer_id differs (different customer used the code)
  - Idempotency: re-running does not overwrite an existing redeemed_at
  - Already-redeemed row + second matching order → first redemption kept
  - NULL customer_id on order → skipped (guest/masked orders)
  - Watermark advances after a successful run
  - Missing fact_orders table in olap → returns 0, no exception

All tests inject candidate_rows directly — no live olap.duckdb is needed.
crm.db tables are bootstrapped from real migration SQL so column names stay
in sync with the production schema.
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

from hug.voucher_redeem_matcher import match_redeemed_vouchers  # noqa: E402
from hug.voucher_repository import get_issuance, record_issuance  # noqa: E402

# ---------------------------------------------------------------------------
# Migration SQL paths
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = pathlib.Path(_REPO_ROOT) / "crm" / "migrations"
_MIGRATION_VOUCHER = _MIGRATIONS_DIR / "0025_hug_voucher_ledger.up.sql"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def crm_conn():
    """In-memory SQLite connection with crm_hug_voucher bootstrapped."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_VOUCHER.read_text(encoding="utf-8"))
    yield c
    c.close()


@pytest.fixture()
def watermark(tmp_path):
    """Return a path to a non-existent watermark file (created on first run)."""
    return str(tmp_path / "hug_redeem_watermark.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue(
    conn: sqlite3.Connection,
    code: str,
    customer_id: str,
    campaign_id: str = "A2",
    issued_at: str = "2026-06-20T00:00:00Z",
) -> None:
    """Seed a voucher issuance row into crm_hug_voucher."""
    record_issuance(
        conn,
        code=code,
        customer_id=customer_id,
        campaign_id=campaign_id,
        issued_at=issued_at,
    )


def _order(
    customer_id: str,
    code: str,
    order_code: str,
    ordered_at: str = "2026-06-20T10:00:00Z",
) -> dict:
    """Build a candidate order dict (mimics a fact_orders row)."""
    return {
        "customer_id": customer_id,
        "code": code,
        "order_code": order_code,
        "ordered_at": ordered_at,
    }


def _watermark_value(path: str) -> str:
    """Read the last_ordered_at from a watermark file, or '' if absent."""
    p = pathlib.Path(path)
    if not p.exists():
        return ""
    return json.loads(p.read_text(encoding="utf-8")).get("last_ordered_at", "")


# ---------------------------------------------------------------------------
# Happy path: matching (customer_id, code) → marks redeemed
# ---------------------------------------------------------------------------

def test_matches_and_sets_redeemed_at(crm_conn, watermark):
    """Issued voucher + matching order (same customer_id + code) → redeemed_at set."""
    _issue(crm_conn, "HUG50", "CUST-001")

    n = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-001", "HUG50", "ORD-001")],
    )

    assert n == 1
    row = get_issuance(crm_conn, "HUG50", "CUST-001")
    assert row is not None
    assert row["redeemed_at"] == "2026-06-20T10:00:00Z"
    assert row["order_code"] == "ORD-001"


# ---------------------------------------------------------------------------
# No match: coupon code differs
# ---------------------------------------------------------------------------

def test_no_match_when_code_differs(crm_conn, watermark):
    """Order coupon code ≠ issued code → 0 updates, row stays unredeemed."""
    _issue(crm_conn, "HUG50", "CUST-002")

    n = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-002", "OTHER_CODE", "ORD-002")],
    )

    assert n == 0
    row = get_issuance(crm_conn, "HUG50", "CUST-002")
    assert row["redeemed_at"] is None


# ---------------------------------------------------------------------------
# No match: customer_id differs (different customer used the same code)
# ---------------------------------------------------------------------------

def test_no_match_when_customer_differs(crm_conn, watermark):
    """HUG50 issued to CUST-A; order placed by CUST-B → no attribution match."""
    _issue(crm_conn, "HUG50", "CUST-A")

    n = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-B", "HUG50", "ORD-003")],
    )

    assert n == 0
    row = get_issuance(crm_conn, "HUG50", "CUST-A")
    assert row["redeemed_at"] is None


# ---------------------------------------------------------------------------
# Idempotency: re-run does not overwrite existing redeemed_at
# ---------------------------------------------------------------------------

def test_idempotent_already_redeemed(crm_conn, watermark):
    """Re-running matcher on a row that was already marked redeemed → no overwrite."""
    _issue(crm_conn, "HUG50", "CUST-003")

    # First run marks it redeemed.
    n1 = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-003", "HUG50", "ORD-004", ordered_at="2026-06-20T10:00:00Z")],
    )
    assert n1 == 1

    # Advance watermark manually so the re-injection seam lets the second row through.
    # (In production the watermark would be ahead; in tests we inject a later ordered_at.)
    n2 = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-003", "HUG50", "ORD-004-AGAIN", ordered_at="2026-06-20T11:00:00Z")],
    )
    assert n2 == 0  # WHERE redeemed_at IS NULL filters it out

    row = get_issuance(crm_conn, "HUG50", "CUST-003")
    assert row["order_code"] == "ORD-004"           # first order kept
    assert row["redeemed_at"] == "2026-06-20T10:00:00Z"  # original timestamp kept


# ---------------------------------------------------------------------------
# Already-redeemed row + second matching order → first redemption preserved
# ---------------------------------------------------------------------------

def test_second_order_does_not_overwrite_first_redemption(crm_conn, watermark):
    """If somehow two orders share (customer_id, code), the first redeem wins."""
    _issue(crm_conn, "HUG50", "CUST-004")

    # Seed first redemption directly via repository to simulate prior state.
    from hug.voucher_repository import mark_redeemed
    mark_redeemed(
        crm_conn,
        code="HUG50",
        customer_id="CUST-004",
        order_code="ORD-FIRST",
        redeemed_at="2026-06-19T08:00:00Z",
    )

    # Matcher encounters a later order with the same (customer, code).
    n = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-004", "HUG50", "ORD-SECOND", ordered_at="2026-06-20T12:00:00Z")],
    )

    assert n == 0  # already redeemed — WHERE redeemed_at IS NULL suppresses it
    row = get_issuance(crm_conn, "HUG50", "CUST-004")
    assert row["order_code"] == "ORD-FIRST"
    assert row["redeemed_at"] == "2026-06-19T08:00:00Z"


# ---------------------------------------------------------------------------
# NULL customer_id on order → skipped (watermark still advances)
# ---------------------------------------------------------------------------

def test_skips_null_customer_id(crm_conn, watermark):
    """Orders without a customer_id (guest/masked) are excluded from candidates."""
    _issue(crm_conn, "HUG50", "CUST-005")

    # Simulate injection seam filtering out NULL customer_id (as olap query does)
    # by passing a row with customer_id=None.  The seam itself doesn't filter by
    # customer_id, but the UPDATE WHERE clause won't match any row.
    n = match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[
            {
                "customer_id": None,
                "code": "HUG50",
                "order_code": "ORD-GUEST",
                "ordered_at": "2026-06-20T13:00:00Z",
            }
        ],
    )

    # The UPDATE matches on customer_id = None which never matches a real row.
    assert n == 0
    row = get_issuance(crm_conn, "HUG50", "CUST-005")
    assert row["redeemed_at"] is None


# ---------------------------------------------------------------------------
# Watermark advances after a run
# ---------------------------------------------------------------------------

def test_watermark_advances(crm_conn, watermark):
    """Watermark JSON is created/updated to max(ordered_at) of the scanned batch."""
    _issue(crm_conn, "HUG50", "CUST-006")

    ts = "2026-06-20T14:00:00Z"
    match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[_order("CUST-006", "HUG50", "ORD-006", ordered_at=ts)],
    )

    assert _watermark_value(watermark) == ts


def test_watermark_advances_to_latest_in_batch(crm_conn, watermark):
    """When multiple orders are processed, watermark advances to the latest ordered_at."""
    _issue(crm_conn, "HUG50", "CUST-007")
    _issue(crm_conn, "HUG60", "CUST-008", campaign_id="A3")

    match_redeemed_vouchers(
        crm_conn, "", watermark,
        candidate_rows=[
            _order("CUST-007", "HUG50", "ORD-007a", ordered_at="2026-06-20T09:00:00Z"),
            _order("CUST-008", "HUG60", "ORD-007b", ordered_at="2026-06-20T15:00:00Z"),
        ],
    )

    assert _watermark_value(watermark) == "2026-06-20T15:00:00Z"


# ---------------------------------------------------------------------------
# Missing fact_orders table in olap → returns 0, no exception
# ---------------------------------------------------------------------------

def test_missing_fact_orders_table_returns_zero_gracefully(crm_conn, watermark, tmp_path):
    """When fact_orders is absent from olap.duckdb, matcher returns 0 without crashing."""
    import duckdb

    # Create a real (but empty) DuckDB file — no fact_orders table.
    olap_path = str(tmp_path / "empty_olap.duckdb")
    con = duckdb.connect(olap_path)
    con.close()

    # Call without candidate_rows — forces the real DuckDB code path.
    n = match_redeemed_vouchers(crm_conn, olap_path, watermark)
    assert n == 0  # must not raise
