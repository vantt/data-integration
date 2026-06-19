"""test_hug_token_provisioning.py — unit tests for the Hug local token master.

Covers: token charset/length/format, mint uniqueness, claim/bind lifecycle,
and the config-gated D1 push (skips gracefully when HUG_WORKER_URL is unset).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug import config as hug_config  # noqa: E402
from hug import d1_push, repository  # noqa: E402
from hug import db as hug_db  # noqa: E402
from hug import tokens  # noqa: E402


@pytest.fixture()
def hug_conn(tmp_path):
    conn = hug_db.connect(str(tmp_path / "hug.db"))
    yield conn
    conn.close()


# ── tokens ────────────────────────────────────────────────────────────────────

def test_token_charset_and_length():
    forbidden = set("ILO01")
    for _ in range(500):
        t = tokens.generate_token()
        assert len(t) == 12
        assert tokens.is_valid_token(t)
        assert not (set(t) & forbidden), f"forbidden char in {t}"
        assert t == t.upper()


def test_human_code_format():
    assert tokens.human_code("ABCDEFGH2345") == "HUG-ABCD-EFGH-2345"


def test_token_generation_is_random():
    sample = {tokens.generate_token() for _ in range(1000)}
    assert len(sample) == 1000  # no dup in 1000 draws over a 7.8e17 space


# ── mint ──────────────────────────────────────────────────────────────────────

def test_mint_batch_unique_and_printed(hug_conn):
    minted = repository.mint_batch(hug_conn, 20, batch_id="B-test", op_type="package_insert")
    assert len(minted) == 20
    assert len(set(minted)) == 20  # all unique

    rows = repository.list_batch(hug_conn, "B-test")
    assert len(rows) == 20
    for r in rows:
        assert r["status"] == "printed"
        assert r["op_type"] == "package_insert"
        assert r["batch_id"] == "B-test"
        assert r["order_code"] is None
        assert tokens.is_valid_token(r["token"])


def test_mint_count_validation(hug_conn):
    with pytest.raises(ValueError):
        repository.mint_batch(hug_conn, 0, batch_id="B-x")


# ── claim / bind ───────────────────────────────────────────────────────────────

def test_bind_token_lifecycle(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-bind")
    row = repository.bind_token(
        hug_conn, tok, order_code="SO1234", op_type="package_insert", is_gift=True
    )
    assert row["status"] == "bound"
    assert row["order_code"] == "SO1234"
    assert row["is_gift"] == 1
    assert row["bound_at"] is not None


def test_bind_unknown_token_raises(hug_conn):
    with pytest.raises(KeyError):
        repository.bind_token(hug_conn, "ZZZZZZZZZZZZ", order_code="SO1")


def test_rebind_same_order_ok_different_order_rejected(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-re")
    repository.bind_token(hug_conn, tok, order_code="SO1")
    # same order — allowed (idempotent re-scan)
    repository.bind_token(hug_conn, tok, order_code="SO1", is_gift=True)
    # different order — rejected
    with pytest.raises(ValueError):
        repository.bind_token(hug_conn, tok, order_code="SO2")


# ── D1 push gating ─────────────────────────────────────────────────────────────

def test_push_skipped_when_worker_url_unset(hug_conn, monkeypatch):
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)
    assert hug_config.push_enabled() is False

    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-push")
    row = repository.bind_token(hug_conn, tok, order_code="SO9")
    result = d1_push.push_bound_token(row)
    assert result["skipped"] is True
    assert result["ok"] is False
    assert "pending deploy" in result["reason"]


def test_push_skipped_when_secret_missing(hug_conn, monkeypatch):
    monkeypatch.setenv("HUG_WORKER_URL", "https://worker.example.com")
    monkeypatch.delenv("HUG_ADMIN_SECRET", raising=False)
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-nosecret")
    row = repository.bind_token(hug_conn, tok, order_code="SO9")
    result = d1_push.push_bound_token(row)
    assert result["skipped"] is True
    assert "secret" in result["reason"].lower()


def test_sign_is_hmac_sha256_hex(monkeypatch):
    sig = d1_push._sign("secret", b'{"a":1}')
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64  # 32-byte digest -> 64 hex chars


def test_d1_payload_matches_worker_contract(hug_conn):
    """Edge row must carry exactly the Worker's HugTokenRow fields, no is_gift."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-contract")
    row = repository.bind_token(
        hug_conn, tok, order_code="SO5", op_type="package_insert", is_gift=True
    )
    payload = d1_push._row_to_payload(row)
    assert set(payload.keys()) == {
        "token", "customer_id", "op_type", "order_code", "channel",
        "ship_date", "sku", "campaign_hint", "status", "batch_id",
    }
    assert "is_gift" not in payload  # local-only, never pushed to edge
    assert payload["status"] == "bound"
    assert payload["order_code"] == "SO5"
