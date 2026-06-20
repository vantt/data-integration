"""test_hug_customer_push.py — unit tests for the nightly hug_customer edge push.

Covers:
  C1  CRM-captured phone → is_contactable=1 even when warehouse says 0  (Option A core)
  C2  Warehouse-contactable customer stays is_contactable=1
  C3  Non-contactable customer (neither warehouse nor CRM) stays 0
  C4  POST body matches edge contract shape
  C5  HMAC signature + explicit User-Agent headers are set (mocked HTTP)
  C6  HUG_WORKER_URL unset → skips cleanly, no HTTP, no crash
  C7  crm_identity_link needs_review row is NOT counted as contactable
  C8  Null scanner_phone in identity_link is NOT counted as contactable
"""
from __future__ import annotations

import hashlib
import hmac
import json
import pathlib
import sqlite3
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root and crm/src are importable.
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug import customer_push  # noqa: E402
from hug import d1_transport    # noqa: E402


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_cache_db(path: str, rows: list[dict]) -> None:
    """Seed a minimal cache.db with wh_customer_tier rows."""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wh_customer_tier (
            customer_key    TEXT PRIMARY KEY,
            customer_id     INTEGER,
            strategic_tier  TEXT,
            recency_days    INTEGER,
            value_group     TEXT,
            is_contactable  INTEGER
        )
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO wh_customer_tier "
            "(customer_key, customer_id, strategic_tier, recency_days, value_group, is_contactable) "
            "VALUES (:customer_key, :customer_id, :strategic_tier, :recency_days, :value_group, :is_contactable)",
            r,
        )
    conn.commit()
    conn.close()


def _make_crm_db(path: str, link_rows: list[dict]) -> None:
    """Seed a minimal crm.db with crm_identity_link rows."""
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crm_identity_link (
            token                TEXT NOT NULL,
            buyer_customer_id    TEXT,
            scanner_phone        TEXT,
            scanner_zalo_uid     TEXT,
            resolved_customer_id TEXT,
            confidence           REAL NOT NULL DEFAULT 1.0,
            status               TEXT NOT NULL,
            ts                   TEXT NOT NULL,
            UNIQUE (token, scanner_phone)
        )
    """)
    for r in link_rows:
        conn.execute(
            "INSERT OR IGNORE INTO crm_identity_link "
            "(token, buyer_customer_id, scanner_phone, resolved_customer_id, confidence, status, ts) "
            "VALUES (:token, :buyer_customer_id, :scanner_phone, :resolved_customer_id, "
            "        :confidence, :status, :ts)",
            r,
        )
    conn.commit()
    conn.close()


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ─── _build_edge_rows unit tests (pure logic, no I/O) ─────────────────────

def test_crm_overlay_makes_masked_customer_contactable():
    """C1: warehouse is_contactable=0, CRM has linked phone → edge must show 1."""
    tier_rows = [
        {"customer_id": 42, "strategic_tier": "MASKED_REPEAT",
         "recency_days": 10, "value_group": "GOLD", "is_contactable": 0},
    ]
    crm_contactable = {"42"}  # CRM captured a phone for customer 42
    rows = customer_push._build_edge_rows(tier_rows, crm_contactable)
    assert len(rows) == 1
    assert rows[0]["is_contactable"] == 1


def test_warehouse_contactable_stays_contactable():
    """C2: warehouse is_contactable=1 (no CRM entry) → edge must show 1."""
    tier_rows = [
        {"customer_id": 7, "strategic_tier": "LIVE_CORE",
         "recency_days": 5, "value_group": "VIP", "is_contactable": 1},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["is_contactable"] == 1


def test_non_contactable_stays_zero():
    """C3: neither warehouse nor CRM → is_contactable=0."""
    tier_rows = [
        {"customer_id": 99, "strategic_tier": "GRAVEYARD",
         "recency_days": 400, "value_group": "BRONZE", "is_contactable": 0},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["is_contactable"] == 0


def test_edge_row_shape_matches_contract():
    """C4: every edge row has exactly the fields the Worker expects."""
    tier_rows = [
        {"customer_id": 1, "strategic_tier": "SECOND_ORDER",
         "recency_days": 30, "value_group": "SILVER", "is_contactable": 1},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert len(rows) == 1
    assert set(rows[0].keys()) == {"customer_id", "tier", "recency_days", "value_group", "is_contactable"}
    assert rows[0]["tier"] == "SECOND_ORDER"   # strategic_tier mapped to "tier"
    assert rows[0]["customer_id"] == "1"        # cast to str


# ─── HTTP mock: verify auth headers ──────────────────────────────────────────

def test_push_sets_hmac_and_explicit_user_agent(tmp_dir, monkeypatch):
    """C5: POST to Worker carries HMAC signature and a non-default User-Agent."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [
        {"customer_key": "k1", "customer_id": 1, "strategic_tier": "LIVE_CORE",
         "recency_days": 3, "value_group": "VIP", "is_contactable": 1},
    ])
    _make_crm_db(crm_path, [])

    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    captured: list[dict] = []

    def fake_urlopen(req, timeout=None):
        captured.append({
            "url":    req.full_url,
            "ua":     req.get_header("User-agent"),
            "sig":    req.get_header("X-hug-signature"),
            "body":   req.data,
        })
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path)

    assert not result.get("skipped")
    assert result.get("ok", 0) >= 1
    assert len(captured) >= 1

    call = captured[0]
    # User-Agent must NOT be the default Python-urllib UA (Bot Fight Mode blocks it).
    assert call["ua"] != "Python-urllib"
    assert call["ua"] == "FineJapan-Hug-Push/1.0"

    # Signature must be valid HMAC-SHA256.
    sig_header = call["sig"]
    assert sig_header.startswith("sha256=")
    expected = "sha256=" + hmac.new(
        b"test-secret", call["body"], hashlib.sha256
    ).hexdigest()
    assert sig_header == expected

    # Body must be valid JSON with "rows" list.
    body = json.loads(call["body"])
    assert "rows" in body
    assert isinstance(body["rows"], list)
    row = body["rows"][0]
    assert set(row.keys()) == {"customer_id", "tier", "recency_days", "value_group", "is_contactable"}


# ─── Config-gating ────────────────────────────────────────────────────────────

def test_skip_when_worker_url_unset(tmp_dir, monkeypatch):
    """C6: HUG_WORKER_URL unset → returns skipped, never calls urlopen."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [
        {"customer_key": "k1", "customer_id": 1, "strategic_tier": "LIVE_CORE",
         "recency_days": 3, "value_group": "VIP", "is_contactable": 1},
    ])
    _make_crm_db(crm_path, [])

    monkeypatch.delenv("HUG_WORKER_URL", raising=False)

    with patch("urllib.request.urlopen") as mock_open:
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path)

    assert result["skipped"] is True
    assert "pending deploy" in result.get("reason", "")
    mock_open.assert_not_called()


# ─── CRM overlay edge cases ──────────────────────────────────────────────────

def test_needs_review_link_not_counted_as_contactable(tmp_dir):
    """C7: needs_review rows must NOT flip is_contactable to 1."""
    crm_path = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_crm_db(crm_path, [
        {
            "token": "TOK1", "buyer_customer_id": "55",
            "scanner_phone": "0901000055", "resolved_customer_id": "55",
            "confidence": 0.5, "status": "needs_review",
            "ts": "2026-06-20T00:00:00Z",
        },
    ])
    contactable = customer_push._load_crm_contactable_ids(crm_path)
    assert "55" not in contactable


def test_null_scanner_phone_not_counted_as_contactable(tmp_dir):
    """C8: Zalo-only opt-in (NULL scanner_phone) must NOT flip is_contactable."""
    crm_path = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_crm_db(crm_path, [
        {
            "token": "TOK2", "buyer_customer_id": "66",
            "scanner_phone": None, "resolved_customer_id": "66",
            "confidence": 1.0, "status": "linked",
            "ts": "2026-06-20T00:00:00Z",
        },
    ])
    contactable = customer_push._load_crm_contactable_ids(crm_path)
    assert "66" not in contactable
