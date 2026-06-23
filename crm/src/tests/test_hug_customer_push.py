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

Incremental content-diff push (hug_push_state.db):
  D1  First run bootstraps store and pushes all rows
  D2  Second run, no change → zero API calls
  D3  One row's tier changed → only that row pushed, store updated
  D4  Batch failure does NOT update store for that batch's rows
  D5  force=True bypasses store and pushes all rows
  D6  HUG_CUSTOMER_PUSH_FULL=1 env var triggers force run
  D7  New customer not in store is pushed; unchanged customers skipped
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
            is_contactable  INTEGER,
            customer_type   TEXT
        )
    """)
    for r in rows:
        conn.execute(
            "INSERT INTO wh_customer_tier "
            "(customer_key, customer_id, strategic_tier, recency_days, value_group, is_contactable, customer_type) "
            "VALUES (:customer_key, :customer_id, :strategic_tier, :recency_days, :value_group, :is_contactable, :customer_type)",
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


@pytest.fixture()
def state_db(tmp_dir):
    """Path to a fresh hug_push_state.db (created lazily by run())."""
    return str(pathlib.Path(tmp_dir) / "hug_push_state.db")


def _capturing_urlopen(captured: list[dict]):
    """Return a fake urlopen that records each POST body and returns HTTP 200."""
    def fake(req, timeout=None):
        captured.append({"url": req.full_url, "body": req.data})
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    return fake


def _state_count(path: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM hug_customer_push_state").fetchone()[0]
    finally:
        conn.close()


def _state_content(path: str, customer_id: str) -> str | None:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT content FROM hug_customer_push_state WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


_ROW_1 = {"customer_key": "k1", "customer_id": 1, "strategic_tier": "LIVE_CORE",
          "recency_days": 3, "value_group": "VIP", "is_contactable": 1, "customer_type": "RETAIL"}
_ROW_2 = {"customer_key": "k2", "customer_id": 2, "strategic_tier": "GRAVEYARD",
          "recency_days": 400, "value_group": "LOW", "is_contactable": 0, "customer_type": "WHOLESALE"}


# ─── _build_edge_rows unit tests (pure logic, no I/O) ─────────────────────

def test_crm_overlay_makes_masked_customer_contactable():
    """C1: warehouse is_contactable=0, CRM has linked phone → edge must show 1."""
    tier_rows = [
        {"customer_id": 42, "strategic_tier": "MASKED_REPEAT",
         "recency_days": 10, "value_group": "GOLD", "is_contactable": 0, "customer_type": "RETAIL"},
    ]
    crm_contactable = {"42"}  # CRM captured a phone for customer 42
    rows = customer_push._build_edge_rows(tier_rows, crm_contactable)
    assert len(rows) == 1
    assert rows[0]["is_contactable"] == 1


def test_warehouse_contactable_stays_contactable():
    """C2: warehouse is_contactable=1 (no CRM entry) → edge must show 1."""
    tier_rows = [
        {"customer_id": 7, "strategic_tier": "LIVE_CORE",
         "recency_days": 5, "value_group": "VIP", "is_contactable": 1, "customer_type": "RETAIL"},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["is_contactable"] == 1


def test_non_contactable_stays_zero():
    """C3: neither warehouse nor CRM → is_contactable=0."""
    tier_rows = [
        {"customer_id": 99, "strategic_tier": "GRAVEYARD",
         "recency_days": 400, "value_group": "BRONZE", "is_contactable": 0, "customer_type": None},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["is_contactable"] == 0


def test_edge_row_shape_matches_contract():
    """C4: every edge row has exactly the fields the Worker expects."""
    tier_rows = [
        {"customer_id": 1, "strategic_tier": "SECOND_ORDER",
         "recency_days": 30, "value_group": "SILVER", "is_contactable": 1, "customer_type": "WHOLESALE"},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert len(rows) == 1
    assert set(rows[0].keys()) == {"customer_id", "tier", "recency_days", "value_group", "is_contactable", "customer_type"}
    assert rows[0]["tier"] == "SECOND_ORDER"   # strategic_tier mapped to "tier"
    assert rows[0]["customer_id"] == "1"        # cast to str


# ─── HTTP mock: verify auth headers ──────────────────────────────────────────

def test_push_sets_hmac_and_explicit_user_agent(tmp_dir, monkeypatch, state_db):
    """C5: POST to Worker carries HMAC signature and a non-default User-Agent."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [
        {"customer_key": "k1", "customer_id": 1, "strategic_tier": "LIVE_CORE",
         "recency_days": 3, "value_group": "VIP", "is_contactable": 1, "customer_type": "RETAIL"},
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
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

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

    # Body must be valid JSON with "rows" list including customer_type.
    body = json.loads(call["body"])
    assert "rows" in body
    assert isinstance(body["rows"], list)
    row = body["rows"][0]
    assert set(row.keys()) == {"customer_id", "tier", "recency_days", "value_group", "is_contactable", "customer_type"}


# ─── Config-gating ────────────────────────────────────────────────────────────

def test_skip_when_worker_url_unset(tmp_dir, monkeypatch):
    """C6: HUG_WORKER_URL unset → returns skipped, never calls urlopen."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [
        {"customer_key": "k1", "customer_id": 1, "strategic_tier": "LIVE_CORE",
         "recency_days": 3, "value_group": "VIP", "is_contactable": 1, "customer_type": "RETAIL"},
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


# ─── Incremental content-diff push (hug_push_state.db) ───────────────────────

def _enable_push(monkeypatch):
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")


def test_first_run_bootstraps_store_and_pushes_all(tmp_dir, monkeypatch, state_db):
    """D1: empty store → all rows pushed, store seeded with their content."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [_ROW_1, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    captured: list[dict] = []
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen(captured)):
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    assert not result.get("skipped")
    assert result["ok"] == 2
    assert len(captured) >= 1
    assert pathlib.Path(state_db).exists()
    assert _state_count(state_db) == 2
    # Content matches the pushed-field contract (5-field format including customer_type).
    assert _state_content(state_db, "1") == "LIVE_CORE|3|VIP|1|RETAIL"


def test_second_run_no_change_skips_all_api(tmp_dir, monkeypatch, state_db):
    """D2: unchanged mart → no-change skip, zero urlopen calls."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [_ROW_1, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    # First run populates the store.
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen([])):
        customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    # Second run on identical data must not hit the network.
    with patch("urllib.request.urlopen") as mock_open:
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    assert result == {"skipped": True, "reason": "no-change"}
    mock_open.assert_not_called()


def test_changed_row_pushes_only_that_row(tmp_dir, monkeypatch, state_db):
    """D3: one customer's tier changed → exactly that row pushed, store updated."""
    cache_v1 = str(pathlib.Path(tmp_dir) / "cache_v1.db")
    cache_v2 = str(pathlib.Path(tmp_dir) / "cache_v2.db")
    crm_path = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_v1, [_ROW_1, _ROW_2])
    # cid=1 tier flips; cid=2 unchanged.
    row_1_changed = {**_ROW_1, "strategic_tier": "SECOND_ORDER"}
    _make_cache_db(cache_v2, [row_1_changed, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen([])):
        customer_push.run(cache_db=cache_v1, crm_db=crm_path, state_db=state_db)

    captured: list[dict] = []
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen(captured)):
        result = customer_push.run(cache_db=cache_v2, crm_db=crm_path, state_db=state_db)

    assert result["total"] == 1
    assert result["ok"] == 1
    # Exactly one row in the POST body, and it is the changed customer.
    body = json.loads(captured[0]["body"])
    assert len(body["rows"]) == 1
    assert body["rows"][0]["customer_id"] == "1"
    assert body["rows"][0]["tier"] == "SECOND_ORDER"
    # Store: cid=1 updated, cid=2 unchanged.
    assert _state_content(state_db, "1") == "SECOND_ORDER|3|VIP|1|RETAIL"
    assert _state_content(state_db, "2") == "GRAVEYARD|400|LOW|0|WHOLESALE"


def test_failed_batch_does_not_update_store(tmp_dir, monkeypatch, state_db):
    """D4: a failed batch leaves the store untouched → retried next run."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [_ROW_1, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    # post_signed failure shape: {"ok": False, "error": "http 500"} (no status key).
    fail = {"ok": False, "error": "http 500"}
    with patch("hug.customer_push.post_signed", return_value=fail) as mock_post:
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    assert result["failed"] == 2
    assert result["ok"] == 0
    # No batch succeeded → store stays empty.
    assert _state_count(state_db) == 0

    # Next run retries (store still empty → all rows still "changed").
    with patch("hug.customer_push.post_signed", return_value=fail) as mock_post2:
        customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)
    assert mock_post2.called


def test_force_param_pushes_all_despite_current_store(tmp_dir, monkeypatch, state_db):
    """D5: force=True bypasses the diff and re-pushes everything."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [_ROW_1, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen([])):
        customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    captured: list[dict] = []
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen(captured)):
        result = customer_push.run(
            cache_db=cache_path, crm_db=crm_path, state_db=state_db, force=True,
        )

    assert not result.get("skipped")
    assert result["ok"] == 2
    assert len(captured) >= 1


def test_env_var_triggers_force_run(tmp_dir, monkeypatch, state_db):
    """D6: HUG_CUSTOMER_PUSH_FULL=1 forces a full push via env (no force kwarg)."""
    cache_path = str(pathlib.Path(tmp_dir) / "cache.db")
    crm_path   = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_path, [_ROW_1, _ROW_2])
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen([])):
        customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    monkeypatch.setenv("HUG_CUSTOMER_PUSH_FULL", "1")
    captured: list[dict] = []
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen(captured)):
        result = customer_push.run(cache_db=cache_path, crm_db=crm_path, state_db=state_db)

    assert not result.get("skipped")
    assert result["ok"] == 2


def test_new_customer_pushed_unchanged_skipped(tmp_dir, monkeypatch, state_db):
    """D7: a customer absent from the store is pushed; unchanged ones are skipped."""
    cache_v1 = str(pathlib.Path(tmp_dir) / "cache_v1.db")
    cache_v2 = str(pathlib.Path(tmp_dir) / "cache_v2.db")
    crm_path = str(pathlib.Path(tmp_dir) / "crm.db")
    _make_cache_db(cache_v1, [_ROW_1])            # store seeded with cid=1 only
    _make_cache_db(cache_v2, [_ROW_1, _ROW_2])    # cid=2 is new
    _make_crm_db(crm_path, [])
    _enable_push(monkeypatch)

    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen([])):
        customer_push.run(cache_db=cache_v1, crm_db=crm_path, state_db=state_db)

    captured: list[dict] = []
    with patch("urllib.request.urlopen", side_effect=_capturing_urlopen(captured)):
        result = customer_push.run(cache_db=cache_v2, crm_db=crm_path, state_db=state_db)

    assert result["total"] == 1
    assert result["ok"] == 1
    body = json.loads(captured[0]["body"])
    assert len(body["rows"]) == 1
    assert body["rows"][0]["customer_id"] == "2"


# ─── customer_type passthrough tests ─────────────────────────────────────────

def test_customer_type_passed_through_to_edge_row():
    """E1: customer_type from mart passes through to the edge row dict unchanged."""
    tier_rows = [
        {"customer_id": 10, "strategic_tier": "VIP", "recency_days": 2,
         "value_group": "HIGH", "is_contactable": 1, "customer_type": "WHOLESALE"},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["customer_type"] == "WHOLESALE"


def test_customer_type_none_when_missing_from_mart():
    """E2: row with customer_type=None in mart → None in edge row (not an error)."""
    tier_rows = [
        {"customer_id": 11, "strategic_tier": "NEW", "recency_days": 0,
         "value_group": "LOW", "is_contactable": 0, "customer_type": None},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    assert rows[0]["customer_type"] is None


def test_customer_type_empty_string_normalized_to_none():
    """E3: empty string customer_type from mart normalizes to None in edge row."""
    tier_rows = [
        {"customer_id": 12, "strategic_tier": "CASUAL", "recency_days": 60,
         "value_group": "MID", "is_contactable": 0, "customer_type": ""},
    ]
    rows = customer_push._build_edge_rows(tier_rows, set())
    # _build_edge_rows uses `r.get("customer_type") or None` → "" becomes None.
    assert rows[0]["customer_type"] is None


def test_content_str_includes_customer_type():
    """E4: _content_str produces 5-field pipe-delimited string with customer_type last."""
    row = {"tier": "VIP", "recency_days": 5, "value_group": "HIGH",
           "is_contactable": 1, "customer_type": "RETAIL"}
    result = customer_push._content_str(row)
    assert result == "VIP|5|HIGH|1|RETAIL"


def test_content_str_null_customer_type_uses_empty_string():
    """E5: _content_str with None customer_type produces empty trailing field."""
    row = {"tier": "CORE", "recency_days": 30, "value_group": "MID",
           "is_contactable": 0, "customer_type": None}
    result = customer_push._content_str(row)
    assert result == "CORE|30|MID|0|"


def test_content_str_field_count_is_five():
    """E6: _content_str always produces exactly 5 pipe-separated fields."""
    row = {"tier": "NEW", "recency_days": 0, "value_group": "LOW",
           "is_contactable": 0, "customer_type": "CROSSBORDER"}
    parts = customer_push._content_str(row).split("|")
    assert len(parts) == 5
