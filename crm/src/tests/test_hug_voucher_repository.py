"""test_hug_voucher_repository.py — unit tests for voucher_repository.py.

Covers:
  - migration creates crm_hug_voucher table and v_hug_voucher_attribution view
  - migration is idempotent (safe to apply twice)
  - record_issuance: inserts new row, returns True
  - record_issuance: duplicate (code, customer_id) is ignored, returns False
  - get_issuance: returns row when found, None when missing
  - list_unredeemed: only returns rows where redeemed_at IS NULL
  - list_unredeemed: campaign_id filter
  - mark_redeemed: sets redeemed_at + order_code, returns True
  - mark_redeemed: already-redeemed row is not overwritten, returns False
  - mark_redeemed: unknown (code, customer_id) returns False
  - attribution_rows: correct issued/redeemed counts and redeem_rate_pct
  - attribution_rows: campaign_id filter
  - record_issuance: raises ValueError on empty required fields

All tests use an in-memory SQLite connection with migration 0025 applied
directly — no FastAPI, no CRMDatabase fixture, no subprocess.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

import pytest

_REPO_ROOT   = str(pathlib.Path(__file__).parents[3])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])    # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.voucher_repository import (   # noqa: E402
    attribution_rows,
    get_issuance,
    list_unredeemed,
    mark_redeemed,
    record_issuance,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0025_hug_voucher_ledger.up.sql"
)


@pytest.fixture()
def conn():
    """In-memory SQLite connection with migration 0025 applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _issue(conn, *, code="HUG50", customer_id="C001", campaign_id="A2", **kw):
    """Helper: record a single issuance with sensible defaults."""
    return record_issuance(
        conn,
        code=code,
        customer_id=customer_id,
        campaign_id=campaign_id,
        **kw,
    )


# ---------------------------------------------------------------------------
# Migration smoke-tests
# ---------------------------------------------------------------------------

def test_migration_creates_table(conn):
    """crm_hug_voucher must exist after applying the migration."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "crm_hug_voucher" in tables


def test_migration_creates_view(conn):
    """v_hug_voucher_attribution must exist after applying the migration."""
    views = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
    }
    assert "v_hug_voucher_attribution" in views


def test_migration_idempotent():
    """Applying migration SQL twice on the same DB must not raise."""
    sql = _MIGRATION_PATH.read_text(encoding="utf-8")
    c = sqlite3.connect(":memory:")
    c.executescript(sql)
    c.executescript(sql)   # second apply — IF NOT EXISTS guards must fire
    c.close()


# ---------------------------------------------------------------------------
# record_issuance — insert
# ---------------------------------------------------------------------------

def test_record_issuance_returns_true_on_new_row(conn):
    result = _issue(conn)
    assert result is True


def test_record_issuance_row_persisted(conn):
    _issue(conn, code="HUG50", customer_id="C001", campaign_id="A2",
           token="tok-abc", min_order=500_000, sku_guard='["SKU-X"]',
           issued_at="2026-06-20T10:00:00Z")

    row = get_issuance(conn, "HUG50", "C001")
    assert row is not None
    assert row["code"]        == "HUG50"
    assert row["customer_id"] == "C001"
    assert row["campaign_id"] == "A2"
    assert row["token"]       == "tok-abc"
    assert row["min_order"]   == 500_000
    assert row["sku_guard"]   == '["SKU-X"]'
    assert row["issued_at"]   == "2026-06-20T10:00:00Z"
    assert row["redeemed_at"] is None
    assert row["order_code"]  is None


# ---------------------------------------------------------------------------
# record_issuance — idempotent duplicate
# ---------------------------------------------------------------------------

def test_record_issuance_duplicate_returns_false(conn):
    _issue(conn)
    result = _issue(conn)   # same (code, customer_id)
    assert result is False


def test_record_issuance_duplicate_no_extra_row(conn):
    _issue(conn)
    _issue(conn)
    count = conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 1


def test_record_issuance_different_customer_is_separate_row(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    count = conn.execute("SELECT COUNT(*) FROM crm_hug_voucher").fetchone()[0]
    assert count == 2


# ---------------------------------------------------------------------------
# get_issuance
# ---------------------------------------------------------------------------

def test_get_issuance_returns_none_when_missing(conn):
    row = get_issuance(conn, "NOTEXIST", "C001")
    assert row is None


def test_get_issuance_returns_correct_row(conn):
    _issue(conn, code="HUG50", customer_id="C001")
    _issue(conn, code="HUG50", customer_id="C002")
    row = get_issuance(conn, "HUG50", "C001")
    assert row["customer_id"] == "C001"


# ---------------------------------------------------------------------------
# list_unredeemed
# ---------------------------------------------------------------------------

def test_list_unredeemed_returns_only_null_redeemed_at(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    mark_redeemed(conn, code="HUG50", customer_id="C001",
                  order_code="ORD-001", redeemed_at="2026-06-20T12:00:00Z")

    rows = list_unredeemed(conn)
    assert len(rows) == 1
    assert rows[0]["customer_id"] == "C002"


def test_list_unredeemed_empty_when_all_redeemed(conn):
    _issue(conn, customer_id="C001")
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-X")
    assert list_unredeemed(conn) == []


def test_list_unredeemed_campaign_filter(conn):
    _issue(conn, campaign_id="A2",  customer_id="C001")
    _issue(conn, campaign_id="B1",  customer_id="C002")

    rows = list_unredeemed(conn, campaign_id="A2")
    assert len(rows) == 1
    assert rows[0]["campaign_id"] == "A2"


def test_list_unredeemed_no_filter_returns_all_pending(conn):
    _issue(conn, campaign_id="A2", customer_id="C001")
    _issue(conn, campaign_id="B1", customer_id="C002")

    rows = list_unredeemed(conn)
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# mark_redeemed
# ---------------------------------------------------------------------------

def test_mark_redeemed_returns_true_on_success(conn):
    _issue(conn)
    result = mark_redeemed(conn, code="HUG50", customer_id="C001",
                           order_code="ORD-001")
    assert result is True


def test_mark_redeemed_sets_fields(conn):
    _issue(conn)
    mark_redeemed(conn, code="HUG50", customer_id="C001",
                  order_code="ORD-001", redeemed_at="2026-06-20T15:30:00Z")

    row = get_issuance(conn, "HUG50", "C001")
    assert row["redeemed_at"] == "2026-06-20T15:30:00Z"
    assert row["order_code"]  == "ORD-001"


def test_mark_redeemed_already_redeemed_returns_false(conn):
    """Second mark_redeemed on same row must not overwrite and must return False."""
    _issue(conn)
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-001")
    result = mark_redeemed(conn, code="HUG50", customer_id="C001",
                           order_code="ORD-DIFFERENT")
    assert result is False


def test_mark_redeemed_does_not_overwrite_first_redemption(conn):
    _issue(conn)
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-001")
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-002")

    row = get_issuance(conn, "HUG50", "C001")
    assert row["order_code"] == "ORD-001"   # first value preserved


def test_mark_redeemed_unknown_row_returns_false(conn):
    result = mark_redeemed(conn, code="GHOST", customer_id="C999",
                           order_code="ORD-X")
    assert result is False


# ---------------------------------------------------------------------------
# attribution_rows / v_hug_voucher_attribution
# ---------------------------------------------------------------------------

def test_attribution_rows_counts_issued_and_redeemed(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    _issue(conn, customer_id="C003")
    # Redeem two of three
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-1")
    mark_redeemed(conn, code="HUG50", customer_id="C002", order_code="ORD-2")

    rows = attribution_rows(conn)
    assert len(rows) == 1
    r = rows[0]
    assert r["issued"]          == 3
    assert r["redeemed"]        == 2
    assert r["redeem_rate_pct"] == pytest.approx(66.7, abs=0.05)


def test_attribution_rows_zero_redeemed(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")

    rows = attribution_rows(conn)
    assert rows[0]["redeemed"]        == 0
    assert rows[0]["redeem_rate_pct"] == pytest.approx(0.0)


def test_attribution_rows_campaign_filter(conn):
    _issue(conn, campaign_id="A2", customer_id="C001")
    _issue(conn, campaign_id="B1", customer_id="C002")
    mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="ORD-1")

    rows = attribution_rows(conn, campaign_id="A2")
    assert len(rows) == 1
    assert rows[0]["campaign_id"]     == "A2"
    assert rows[0]["issued"]          == 1
    assert rows[0]["redeemed"]        == 1
    assert rows[0]["redeem_rate_pct"] == pytest.approx(100.0)


def test_attribution_rows_empty_table(conn):
    rows = attribution_rows(conn)
    assert rows == []


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_record_issuance_raises_on_empty_code(conn):
    with pytest.raises(ValueError, match="code"):
        record_issuance(conn, code="", customer_id="C001", campaign_id="A2")


def test_record_issuance_raises_on_empty_customer_id(conn):
    with pytest.raises(ValueError, match="customer_id"):
        record_issuance(conn, code="HUG50", customer_id="", campaign_id="A2")


def test_record_issuance_raises_on_empty_campaign_id(conn):
    with pytest.raises(ValueError, match="campaign_id"):
        record_issuance(conn, code="HUG50", customer_id="C001", campaign_id="")


def test_mark_redeemed_raises_on_empty_order_code(conn):
    _issue(conn)
    with pytest.raises(ValueError, match="order_code"):
        mark_redeemed(conn, code="HUG50", customer_id="C001", order_code="")
