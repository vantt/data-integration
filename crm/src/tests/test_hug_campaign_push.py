"""test_hug_campaign_push.py — unit tests for campaign_push.py.

Verifies:
  P1  targeting stored as JSON string in crm.db is sent as a JSON OBJECT to edge
  P2  quota_used is NOT present in any push row (edge-owned runtime counter)
  P3  HMAC signature + explicit User-Agent headers are set on push (mocked HTTP)
  P4  push_campaign skips cleanly when HUG_WORKER_URL unset — no HTTP call, no crash
  P5  push_campaign returns ok=False (skipped=True) when HUG_ADMIN_SECRET unset
  P6  push_campaign returns ok=False (skipped=False, error=...) on HTTP failure
  P7  push_all_campaigns sends all non-archived rows in one batch call
  P8  push_all_campaigns skips archived campaigns
  P9  _to_edge_row falls back to {} when targeting is invalid JSON
  P10 push_campaign returns ok=True on success
"""
from __future__ import annotations

import hashlib
import hmac
import json
import pathlib
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[3])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug import campaign_push  # noqa: E402
from hug.campaign_push import _to_edge_row  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIGRATION_PATH = (
    pathlib.Path(__file__).parents[3]
    / "crm" / "migrations" / "0024_hug_campaign_authoring.up.sql"
)


@pytest.fixture()
def conn():
    """In-memory SQLite connection with migration 0024 applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_MIGRATION_PATH.read_text(encoding="utf-8"))
    yield c
    c.close()


def _minimal_row(**overrides) -> dict:
    """Return a minimal crm_hug_campaign dict for push tests."""
    base = {
        "campaign_id":      "test-camp-01",
        "name":             "Test Campaign",
        "targeting":        "{}",
        "destination_type": "zalo_oa",
        "destination_url":  "https://oa.zalo.me/test",
        "offer_ref":        None,
        "priority":         100,
        "schedule_start":   None,
        "schedule_end":     None,
        "quota_total":      None,
        "status":           "active",
        "updated_at":       "2026-06-20T00:00:00.000000Z",
    }
    base.update(overrides)
    return base


def _seed_campaigns(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Insert crm_hug_campaign rows directly for push-level tests."""
    for r in rows:
        conn.execute(
            """
            INSERT INTO crm_hug_campaign
                (campaign_id, name, targeting, destination_type, destination_url,
                 offer_ref, priority, schedule_start, schedule_end, quota_total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["campaign_id"], r["name"], r.get("targeting", "{}"),
                r["destination_type"], r["destination_url"],
                r.get("offer_ref"), r.get("priority", 100),
                r.get("schedule_start"), r.get("schedule_end"),
                r.get("quota_total"), r.get("status", "active"),
            ),
        )
    conn.commit()


def _make_fake_urlopen(status: int = 200):
    """Return a fake urlopen that records the outbound request."""
    captured: list[dict] = []

    def fake_urlopen(req, timeout=None):
        captured.append({
            "url":  req.full_url,
            "ua":   req.get_header("User-agent"),
            "sig":  req.get_header("X-hug-signature"),
            "body": req.data,
        })
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    return fake_urlopen, captured


# ---------------------------------------------------------------------------
# P1 — targeting sent as JSON OBJECT, not string
# ---------------------------------------------------------------------------

def test_targeting_parsed_to_object_in_edge_row():
    """P1: crm.db stores targeting as a JSON string; edge row must be a dict/object."""
    row = _minimal_row(targeting='{"tier": ["VIP", "CORE"], "recency_bucket": ["0-7"]}')
    edge = _to_edge_row(row)
    assert isinstance(edge["targeting"], dict), "targeting must be dict, not str"
    assert edge["targeting"] == {"tier": ["VIP", "CORE"], "recency_bucket": ["0-7"]}


def test_empty_targeting_string_becomes_empty_object():
    """P1b: '{}' string → {} object."""
    edge = _to_edge_row(_minimal_row(targeting="{}"))
    assert edge["targeting"] == {}


# ---------------------------------------------------------------------------
# P2 — quota_used must NOT appear in push rows
# ---------------------------------------------------------------------------

def test_quota_used_absent_from_edge_row():
    """P2: quota_used is an edge-owned runtime counter — CRM must never send it."""
    edge = _to_edge_row(_minimal_row())
    assert "quota_used" not in edge, (
        "quota_used must be omitted so the Worker preserves the live counter"
    )


def test_quota_used_absent_even_when_row_has_extra_keys():
    """P2b: even if caller slips quota_used into the row dict, it must not appear in output."""
    row = _minimal_row()
    row["quota_used"] = 42   # simulate accidental inclusion by caller
    edge = _to_edge_row(row)
    assert "quota_used" not in edge


# ---------------------------------------------------------------------------
# P3 — HMAC signature + explicit User-Agent on every HTTP push
# ---------------------------------------------------------------------------

def test_push_sets_hmac_and_explicit_user_agent(monkeypatch):
    """P3: POST carries HMAC-SHA256 signature and FineJapan-Hug-Push/1.0 User-Agent."""
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    fake_urlopen, captured = _make_fake_urlopen(200)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = campaign_push.push_campaign(_minimal_row())

    assert result["ok"] is True
    assert not result["skipped"]
    assert len(captured) == 1

    call = captured[0]

    # User-Agent must be the explicit value, not the default Python-urllib UA
    # (Cloudflare Bot Fight Mode silently 403s the default UA with error 1010).
    assert call["ua"] == "FineJapan-Hug-Push/1.0"

    # Signature must be valid HMAC-SHA256 over the raw body.
    sig_header = call["sig"]
    assert sig_header.startswith("sha256=")
    expected_sig = "sha256=" + hmac.new(
        b"test-secret", call["body"], hashlib.sha256
    ).hexdigest()
    assert sig_header == expected_sig

    # Body must be valid JSON with "rows" list and targeting as object.
    body = json.loads(call["body"])
    assert "rows" in body
    assert isinstance(body["rows"], list)
    push_row = body["rows"][0]
    assert isinstance(push_row["targeting"], dict)
    assert "quota_used" not in push_row


# ---------------------------------------------------------------------------
# P4 — skip cleanly when HUG_WORKER_URL unset
# ---------------------------------------------------------------------------

def test_push_campaign_skips_when_worker_url_unset(monkeypatch):
    """P4: HUG_WORKER_URL unset → returns skipped=True, no HTTP call, no crash."""
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)

    with patch("urllib.request.urlopen") as mock_open:
        result = campaign_push.push_campaign(_minimal_row())

    assert result["ok"] is False
    assert result["skipped"] is True
    assert "pending deploy" in result.get("reason", "")
    mock_open.assert_not_called()


def test_push_all_campaigns_skips_when_worker_url_unset(conn, monkeypatch):
    """P4b: push_all_campaigns also skips cleanly when HUG_WORKER_URL unset."""
    _seed_campaigns(conn, [_minimal_row()])
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)

    with patch("urllib.request.urlopen") as mock_open:
        result = campaign_push.push_all_campaigns(conn)

    assert result["skipped"] is True
    mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# P5 — skip cleanly when HUG_ADMIN_SECRET unset
# ---------------------------------------------------------------------------

def test_push_campaign_skips_when_secret_missing(monkeypatch):
    """P5: URL set but secret empty → returns skipped=True, no crash."""
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.delenv("HUG_ADMIN_SECRET", raising=False)

    with patch("urllib.request.urlopen") as mock_open:
        result = campaign_push.push_campaign(_minimal_row())

    assert result["ok"] is False
    assert result["skipped"] is True
    assert "secret" in result.get("reason", "")
    mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# P6 — HTTP failure reflected in return value, no raise
# ---------------------------------------------------------------------------

def test_push_campaign_returns_error_on_http_failure(monkeypatch):
    """P6: HTTP error → ok=False, skipped=False, error field set — never raises."""
    import urllib.error
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    def fail_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 500, "Internal Server Error", {}, None
        )

    with patch("urllib.request.urlopen", side_effect=fail_urlopen):
        result = campaign_push.push_campaign(_minimal_row())

    assert result["ok"] is False
    assert result["skipped"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# P7 — push_all_campaigns sends all non-archived in one batch
# ---------------------------------------------------------------------------

def test_push_all_campaigns_sends_all_non_archived_in_one_call(conn, monkeypatch):
    """P7: push_all_campaigns batches active+paused rows in a single POST."""
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    _seed_campaigns(conn, [
        _minimal_row(campaign_id="c-active",  status="active"),
        _minimal_row(campaign_id="c-paused",  status="paused"),
        _minimal_row(campaign_id="c-archived", status="archived"),
    ])

    fake_urlopen, captured = _make_fake_urlopen(200)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = campaign_push.push_all_campaigns(conn)

    # One HTTP call
    assert len(captured) == 1
    body = json.loads(captured[0]["body"])
    sent_ids = {r["campaign_id"] for r in body["rows"]}

    # active + paused sent; archived excluded
    assert "c-active"  in sent_ids
    assert "c-paused"  in sent_ids
    assert "c-archived" not in sent_ids

    assert result["ok"] is True
    assert result["total"] == 2


# ---------------------------------------------------------------------------
# P8 — archived campaigns excluded from reconcile push
# ---------------------------------------------------------------------------

def test_push_all_campaigns_excludes_archived(conn, monkeypatch):
    """P8: archived campaigns must not be sent to the edge."""
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    _seed_campaigns(conn, [
        _minimal_row(campaign_id="only-archived", status="archived"),
    ])

    with patch("urllib.request.urlopen") as mock_open:
        result = campaign_push.push_all_campaigns(conn)

    # No active/paused rows → nothing to send
    mock_open.assert_not_called()
    assert result["ok"] is True
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# P9 — invalid JSON targeting falls back to empty object
# ---------------------------------------------------------------------------

def test_invalid_targeting_json_falls_back_to_empty_object():
    """P9: malformed targeting string must not crash; edge row gets {} instead."""
    edge = _to_edge_row(_minimal_row(targeting="not-valid-json"))
    assert edge["targeting"] == {}


# ---------------------------------------------------------------------------
# P10 — push_campaign returns ok=True on success
# ---------------------------------------------------------------------------

def test_push_campaign_returns_ok_true_on_success(monkeypatch):
    """P10: successful 200 response → ok=True, skipped=False."""
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.setenv("HUG_ADMIN_SECRET", "test-secret")

    fake_urlopen, _ = _make_fake_urlopen(200)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = campaign_push.push_campaign(_minimal_row())

    assert result == {"ok": True, "skipped": False}
