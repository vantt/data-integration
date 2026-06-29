"""test_hug_voucher_attribution_screen.py — tests for the voucher attribution screen.

Covers (no FastAPI TestClient — same pattern as test_hug_mint_reprint.py):
  - empty DB → empty-state message rendered
  - seed a few vouchers (some redeemed, some not) → correct issued/redeemed/rate per campaign
  - render_attribution_page: HTML escaping of special chars in campaign_id / code
  - render_attribution_page: rate colour classes (hi / mid / lo)
  - guard: make_hug_voucher_attribution_router returns a non-None APIRouter

Run:
  PYTHONPATH="crm/src" python -m pytest crm/src/tests/test_hug_voucher_attribution_screen.py -q
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

import pytest

_REPO_ROOT   = str(pathlib.Path(__file__).parents[3])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])   # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.voucher_repository import record_issuance, mark_redeemed                    # noqa: E402
from adapters.inbound.web.screen_hug_voucher_attribution_data import load_attribution  # noqa: E402
from adapters.inbound.web.screen_hug_voucher_attribution_html import (                 # noqa: E402
    render_attribution_page,
)
from adapters.outbound.sqlite.hug_voucher_repository_adapter import (                  # noqa: E402
    HugVoucherRepositoryAdapter,
)

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0025_hug_voucher_ledger.up.sql"
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    """In-memory SQLite with migration 0025 applied (table + view)."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _issue(conn, *, code="HUG50", customer_id, campaign_id="a2-test"):
    record_issuance(conn, code=code, customer_id=customer_id, campaign_id=campaign_id)


def _redeem(conn, *, code="HUG50", customer_id, order_code):
    mark_redeemed(conn, code=code, customer_id=customer_id, order_code=order_code)


# ── load_attribution ──────────────────────────────────────────────────────────

def test_load_attribution_empty_db_returns_empty_list(conn):
    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert rows == []


def test_load_attribution_counts_issued_correctly(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    _issue(conn, customer_id="C003")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert len(rows) == 1
    assert rows[0]["issued"] == 3
    assert rows[0]["campaign_id"] == "a2-test"
    assert rows[0]["code"] == "HUG50"


def test_load_attribution_counts_redeemed_correctly(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    _issue(conn, customer_id="C003")
    _redeem(conn, customer_id="C001", order_code="ORD-1")
    _redeem(conn, customer_id="C002", order_code="ORD-2")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert rows[0]["redeemed"] == 2


def test_load_attribution_rate_pct_rounded(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")
    _issue(conn, customer_id="C003")
    _redeem(conn, customer_id="C001", order_code="ORD-1")
    _redeem(conn, customer_id="C002", order_code="ORD-2")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    # 2/3 * 100 = 66.666... → rounded to 66.7
    assert abs(rows[0]["redeem_rate_pct"] - 66.7) < 0.05


def test_load_attribution_zero_redeemed_shows_zero_rate(conn):
    _issue(conn, customer_id="C001")
    _issue(conn, customer_id="C002")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert rows[0]["redeemed"] == 0
    assert rows[0]["redeem_rate_pct"] == pytest.approx(0.0)


def test_load_attribution_multiple_campaigns_each_counted_separately(conn):
    _issue(conn, customer_id="C001", campaign_id="camp-a")
    _issue(conn, customer_id="C002", campaign_id="camp-a")
    _issue(conn, customer_id="C003", campaign_id="camp-b")
    _redeem(conn, customer_id="C001", order_code="ORD-1")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert len(rows) == 2

    by_camp = {r["campaign_id"]: r for r in rows}
    assert by_camp["camp-a"]["issued"] == 2
    assert by_camp["camp-a"]["redeemed"] == 1
    assert by_camp["camp-b"]["issued"] == 1
    assert by_camp["camp-b"]["redeemed"] == 0


def test_load_attribution_sorted_by_issued_desc(conn):
    _issue(conn, customer_id="C001", campaign_id="small")
    for cid in ("C002", "C003", "C004"):
        _issue(conn, customer_id=cid, campaign_id="large")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    assert rows[0]["campaign_id"] == "large"   # 3 issued > 1 issued


# ── render_attribution_page: empty state ──────────────────────────────────────

def test_render_empty_state_shows_vietnamese_message():
    out = render_attribution_page([])
    assert "Chưa phát hành voucher nào" in out


def test_render_empty_state_is_full_html_page():
    out = render_attribution_page([])
    assert "<!doctype html>" in out
    assert "</html>" in out


# ── render_attribution_page: data rows ───────────────────────────────────────

def test_render_rows_shows_campaign_id_and_code():
    rows = [{"campaign_id": "a2-masked", "code": "HUG50",
             "issued": 5, "redeemed": 2, "redeem_rate_pct": 40.0}]
    out = render_attribution_page(rows)
    assert "a2-masked" in out
    assert "HUG50" in out


def test_render_rows_shows_issued_and_redeemed_counts():
    rows = [{"campaign_id": "camp", "code": "HUG50",
             "issued": 10, "redeemed": 3, "redeem_rate_pct": 30.0}]
    out = render_attribution_page(rows)
    assert ">10<" in out
    assert ">3<" in out


def test_render_rows_shows_rate_pct():
    rows = [{"campaign_id": "camp", "code": "HUG50",
             "issued": 4, "redeemed": 2, "redeem_rate_pct": 50.0}]
    out = render_attribution_page(rows)
    assert "50.0%" in out


def test_render_rows_hi_rate_uses_green_class():
    rows = [{"campaign_id": "camp", "code": "X",
             "issued": 2, "redeemed": 2, "redeem_rate_pct": 100.0}]
    out = render_attribution_page(rows)
    assert "rate-hi" in out


def test_render_rows_mid_rate_uses_amber_class():
    rows = [{"campaign_id": "camp", "code": "X",
             "issued": 5, "redeemed": 1, "redeem_rate_pct": 20.0}]
    out = render_attribution_page(rows)
    assert "rate-mid" in out


def test_render_rows_lo_rate_uses_muted_class():
    rows = [{"campaign_id": "camp", "code": "X",
             "issued": 10, "redeemed": 1, "redeem_rate_pct": 10.0}]
    out = render_attribution_page(rows)
    assert "rate-lo" in out


def test_render_rows_html_escapes_campaign_id():
    rows = [{"campaign_id": "<script>", "code": "X",
             "issued": 1, "redeemed": 0, "redeem_rate_pct": 0.0}]
    out = render_attribution_page(rows)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_rows_none_rate_shows_dash():
    rows = [{"campaign_id": "camp", "code": "X",
             "issued": 1, "redeemed": 0, "redeem_rate_pct": None}]
    out = render_attribution_page(rows)
    assert "—" in out


# ── round-trip: seed DB → load → render ──────────────────────────────────────

def test_roundtrip_seed_load_render(conn):
    """Full round-trip: seed crm.db → load_attribution → render → HTML contains counts."""
    _issue(conn, customer_id="C001", campaign_id="a2-masked-repeat-optin")
    _issue(conn, customer_id="C002", campaign_id="a2-masked-repeat-optin")
    _issue(conn, customer_id="C003", campaign_id="a2-masked-repeat-optin")
    _redeem(conn, customer_id="C001", order_code="ORD-A1")

    rows = load_attribution(HugVoucherRepositoryAdapter(conn))
    out = render_attribution_page(rows)

    assert "a2-masked-repeat-optin" in out
    assert "HUG50" in out
    assert ">3<" in out   # issued
    assert ">1<" in out   # redeemed
    assert "33.3%" in out


# ── guard: router factory returns non-None APIRouter ─────────────────────────

def test_router_factory_returns_non_none():
    """make_hug_voucher_attribution_router must return a non-None APIRouter.

    Import is guarded so the test is skipped gracefully when FastAPI is absent
    in the host Python environment (packages live in the Docker container).
    """
    fastapi = pytest.importorskip("fastapi", reason="fastapi not installed in host env")
    from adapters.inbound.web.screen_hug_voucher_attribution import (
        make_hug_voucher_attribution_router,
    )

    c = sqlite3.connect(":memory:")
    port = HugVoucherRepositoryAdapter(c)
    router = make_hug_voucher_attribution_router(port)
    c.close()

    assert router is not None
    assert isinstance(router, fastapi.APIRouter)
