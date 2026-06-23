"""test_hug_claim_dynamic_fields.py — Phase 2: dynamic claim-field foundation tests.

Covers:
  - CLAIM_FIELDS structure + field metadata assertions
  - VALIDATORS dispatch: sapo_order hybrid (cache hit=valid, miss=amber, error=amber)
  - sapo_order_proxy: cache.db hit, miss, absent db, empty value
  - bind_token: bind_attributes JSON stored, bind_session_id stored
  - bind_token idempotency: same-session rebind allowed, different-session blocked
  - bind_token: bind_session_id=None fallback (form-POST path) → always allows
  - check-token states via direct router function calls (no FastAPI dep)
  - check-field dispatch including sapo_order soft-fail
  - AJAX bind happy path + blocked-by-foreign-session
  - Existing form POST compatibility (no-JS fallback unchanged)
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
from unittest.mock import patch

import pytest

# ── sys.path bootstrap ────────────────────────────────────────────────────────

_REPO_ROOT = str(pathlib.Path(__file__).parents[3])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug import db as hug_db         # noqa: E402
from hug import repository            # noqa: E402
from hug.claim_fields import (        # noqa: E402
    CLAIM_FIELDS,
    VALIDATORS,
    get_field,
    claim_fields_json,
)
from hug.repository import AlreadyBoundError  # noqa: E402
from hug import sapo_order_proxy      # noqa: E402

# FastAPI not in this venv — guard router-level integration tests.
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from adapters.inbound.web.screen_hug_claim import make_hug_claim_router, _PROMOTED_COLS  # noqa: E402
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    _PROMOTED_COLS = frozenset({"order_code", "is_gift"})  # replicate for unit tests

_api_only = pytest.mark.skipif(
    not _FASTAPI_AVAILABLE,
    reason="FastAPI not installed in host Python (runs inside Docker)",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def hug_conn(tmp_path):
    conn = hug_db.connect(str(tmp_path / "hug.db"))
    yield conn
    conn.close()


@pytest.fixture()
def cache_db(tmp_path):
    """Minimal cache.db with wh_order_hdr table populated with one known order."""
    db_path = str(tmp_path / "cache.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE wh_order_hdr (order_id TEXT PRIMARY KEY, order_code TEXT)"
    )
    conn.execute("INSERT INTO wh_order_hdr VALUES ('42', 'SO1234')")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def minted_token(hug_conn):
    """Mint one token and return (conn, token)."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-test")
    return hug_conn, tok


@pytest.fixture()
def api_client(hug_conn):
    """FastAPI TestClient wired to a temp hug.db connection (skipped if no FastAPI)."""
    if not _FASTAPI_AVAILABLE:
        pytest.skip("FastAPI not available")
    app = FastAPI()
    router = make_hug_claim_router(hug_conn)
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=True), hug_conn


# ── 1. CLAIM_FIELDS structure ─────────────────────────────────────────────────

def test_claim_fields_has_order_code():
    keys = [f["key"] for f in CLAIM_FIELDS]
    assert "order_code" in keys


def test_claim_fields_has_is_gift():
    keys = [f["key"] for f in CLAIM_FIELDS]
    assert "is_gift" in keys


def test_order_code_field_edge_true():
    field = get_field("order_code")
    assert field is not None
    assert field["edge"] is True


def test_order_code_field_validate_sapo_order():
    field = get_field("order_code")
    assert field["validate"] == "sapo_order"


def test_order_code_field_required():
    field = get_field("order_code")
    assert field["required"] is True


def test_order_code_field_prefill_is_order():
    field = get_field("order_code")
    assert field["prefill"] == "order"


def test_is_gift_field_no_validator():
    field = get_field("is_gift")
    assert field["validate"] is None


def test_is_gift_field_not_required():
    field = get_field("is_gift")
    assert field["required"] is False


def test_is_gift_field_not_edge():
    field = get_field("is_gift")
    assert field["edge"] is False


def test_get_field_unknown_returns_none():
    assert get_field("nonexistent_field") is None


def test_claim_fields_json_strips_validate_key():
    serialised = claim_fields_json()
    for field in serialised:
        assert "validate" not in field


def test_claim_fields_json_has_required_frontend_keys():
    expected = {"key", "label", "type", "input", "required", "prefill", "edge"}
    for field in claim_fields_json():
        assert expected.issubset(field.keys())


def test_validators_has_sapo_order():
    assert "sapo_order" in VALIDATORS
    assert callable(VALIDATORS["sapo_order"])


def test_promoted_cols_contains_order_code_and_is_gift():
    assert "order_code" in _PROMOTED_COLS
    assert "is_gift" in _PROMOTED_COLS


# ── 2. sapo_order_proxy ───────────────────────────────────────────────────────

def test_proxy_cache_hit_returns_valid(cache_db):
    result = sapo_order_proxy.check_order_exists("SO1234", cache_db=cache_db)
    assert result["ok"] is True
    assert result["source"] == "cache"


def test_proxy_cache_miss_returns_amber(cache_db):
    result = sapo_order_proxy.check_order_exists("SO9999", cache_db=cache_db)
    assert result["ok"] is None
    assert result["source"] == "cache"


def test_proxy_absent_db_returns_amber(tmp_path):
    # Database file does not exist — should soft-fail, never raise
    missing_db = str(tmp_path / "nonexistent.db")
    result = sapo_order_proxy.check_order_exists("SO1234", cache_db=missing_db)
    assert result["ok"] is None


def test_proxy_empty_order_code_returns_invalid(cache_db):
    result = sapo_order_proxy.check_order_exists("", cache_db=cache_db)
    assert result["ok"] is False


def test_proxy_whitespace_only_order_code_returns_invalid(cache_db):
    result = sapo_order_proxy.check_order_exists("   ", cache_db=cache_db)
    assert result["ok"] is False


def test_proxy_never_raises_on_exception():
    """Any unexpected error must degrade to amber, never propagate."""
    with patch("sqlite3.connect", side_effect=RuntimeError("disk full")):
        result = sapo_order_proxy.check_order_exists("SO1")
    assert result["ok"] is None


# ── 3. VALIDATORS["sapo_order"] dispatch ─────────────────────────────────────

def test_validators_sapo_order_calls_proxy(cache_db):
    with patch("hug.sapo_order_proxy.check_order_exists", return_value={"ok": True, "source": "cache", "message": "ok"}) as mock_fn:
        result = VALIDATORS["sapo_order"]("SO1234", None)
    mock_fn.assert_called_once_with("SO1234")
    assert result["ok"] is True


def test_validators_sapo_order_soft_fail_when_proxy_amber():
    with patch("hug.sapo_order_proxy.check_order_exists", return_value={"ok": None, "source": "none", "message": "Sapo down"}):
        result = VALIDATORS["sapo_order"]("SO9999", "session-abc")
    assert result["ok"] is None


# ── 4. bind_token: new columns ────────────────────────────────────────────────

def test_bind_token_stores_bind_session_id(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-session")
    row = repository.bind_token(
        hug_conn, tok,
        order_code="SO1",
        bind_session_id="sess-abc-123",
    )
    assert row["bind_session_id"] == "sess-abc-123"


def test_bind_token_stores_bind_attributes_as_json(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-attrs")
    row = repository.bind_token(
        hug_conn, tok,
        order_code="SO2",
        bind_attributes={"note": "fragile", "priority": 1},
    )
    stored = json.loads(row["bind_attributes"])
    assert stored == {"note": "fragile", "priority": 1}


def test_bind_token_empty_attributes_stored_as_empty_dict(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-empty-attrs")
    row = repository.bind_token(hug_conn, tok, order_code="SO3")
    stored = json.loads(row["bind_attributes"])
    assert stored == {}


def test_bind_token_none_attributes_stored_as_empty_dict(hug_conn):
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-none-attrs")
    row = repository.bind_token(hug_conn, tok, order_code="SO4", bind_attributes=None)
    stored = json.loads(row["bind_attributes"])
    assert stored == {}


# ── 5. bind_token idempotency ─────────────────────────────────────────────────

def test_same_session_rebind_allowed(hug_conn):
    """Same session → mid-operation correction → allow overwrite."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-rebind")
    repository.bind_token(hug_conn, tok, order_code="SO10", bind_session_id="sess-1")
    # Re-bind with same session + is_gift update — must succeed
    row = repository.bind_token(
        hug_conn, tok,
        order_code="SO10",
        is_gift=True,
        bind_session_id="sess-1",
    )
    assert row["is_gift"] == 1
    assert row["bind_session_id"] == "sess-1"


def test_different_session_bind_raises_already_bound_error(hug_conn):
    """Different non-None session → another operator's operation → block."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-block")
    repository.bind_token(hug_conn, tok, order_code="SO20", bind_session_id="sess-A")
    with pytest.raises(AlreadyBoundError, match="different operation"):
        repository.bind_token(hug_conn, tok, order_code="SO20", bind_session_id="sess-B")


def test_no_session_bind_allows_rebind(hug_conn):
    """form-POST path: bind_session_id=None → session check skipped → always allows rebind."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-nosess")
    repository.bind_token(hug_conn, tok, order_code="SO30", bind_session_id=None)
    # Re-bind with no session → no block
    row = repository.bind_token(hug_conn, tok, order_code="SO30", bind_session_id=None)
    assert row["status"] == "bound"


def test_stored_none_session_allows_any_rebind(hug_conn):
    """Stored session is None (old form-POST row) → new session can rebind."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-storedNone")
    repository.bind_token(hug_conn, tok, order_code="SO31", bind_session_id=None)
    # New AJAX session comes in — stored None → allow (no blocking)
    row = repository.bind_token(hug_conn, tok, order_code="SO31", bind_session_id="sess-new")
    assert row["bind_session_id"] == "sess-new"


def test_different_order_still_raises_value_error(hug_conn):
    """Different order_code always raises ValueError (pre-existing behaviour)."""
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-difforder")
    repository.bind_token(hug_conn, tok, order_code="SO40", bind_session_id="sess-X")
    with pytest.raises(ValueError, match="different order"):
        repository.bind_token(hug_conn, tok, order_code="SO41", bind_session_id="sess-X")


def test_unknown_token_raises_key_error(hug_conn):
    with pytest.raises(KeyError):
        repository.bind_token(hug_conn, "ZZZZZZZZZZZZ", order_code="SO1")


# ── 6. Schema columns exist after connect ────────────────────────────────────

def test_schema_has_bind_session_id_column(hug_conn):
    row = hug_conn.execute(
        "SELECT COUNT(*) FROM pragma_table_info('hug_token') WHERE name='bind_session_id'"
    ).fetchone()
    assert row[0] == 1, "bind_session_id column missing from hug_token"


def test_schema_has_bind_attributes_column(hug_conn):
    row = hug_conn.execute(
        "SELECT COUNT(*) FROM pragma_table_info('hug_token') WHERE name='bind_attributes'"
    ).fetchone()
    assert row[0] == 1, "bind_attributes column missing from hug_token"


# ── 7. Router-level integration (FastAPI required) ───────────────────────────

@_api_only
def test_check_token_not_minted(api_client):
    client, conn = api_client
    resp = client.get("/hug/claim/check-token?token=AAAAAAAAAAAA&session=s1")
    assert resp.status_code == 200
    data = resp.json()
    # AAAAAAAAAAAA: A is valid but likely not minted → unknown (or invalid charset check)
    assert data["state"] in ("unknown", "invalid")


@_api_only
def test_check_token_ready(api_client):
    client, conn = api_client
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ck-ready")
    resp = client.get(f"/hug/claim/check-token?token={tok}&session=s1")
    assert resp.status_code == 200
    assert resp.json()["state"] == "ready"


@_api_only
def test_check_token_same_session_rebind_ok(api_client):
    client, conn = api_client
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ck-rebind")
    repository.bind_token(conn, tok, order_code="SO1", bind_session_id="sess-R")
    resp = client.get(f"/hug/claim/check-token?token={tok}&session=sess-R")
    assert resp.json()["state"] == "rebind_ok"


@_api_only
def test_check_token_different_session_blocked(api_client):
    client, conn = api_client
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ck-block")
    repository.bind_token(conn, tok, order_code="SO2", bind_session_id="sess-A")
    resp = client.get(f"/hug/claim/check-token?token={tok}&session=sess-B")
    assert resp.json()["state"] == "blocked"


@_api_only
def test_check_field_unknown_key_returns_400(api_client):
    client, _ = api_client
    resp = client.get("/hug/claim/check-field?key=nonexistent&value=X&session=s1")
    assert resp.status_code == 400


@_api_only
def test_check_field_is_gift_no_validator_returns_ok(api_client):
    client, _ = api_client
    resp = client.get("/hug/claim/check-field?key=is_gift&value=1&session=s1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@_api_only
def test_check_field_order_code_cache_hit(api_client, cache_db, monkeypatch):
    client, _ = api_client
    monkeypatch.setenv("CRM_CACHE_DB", cache_db)
    resp = client.get("/hug/claim/check-field?key=order_code&value=SO1234&session=s1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@_api_only
def test_check_field_order_code_cache_miss_amber(api_client, cache_db, monkeypatch):
    client, _ = api_client
    monkeypatch.setenv("CRM_CACHE_DB", cache_db)
    resp = client.get("/hug/claim/check-field?key=order_code&value=SO9999&session=s1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is None


@_api_only
def test_bind_ajax_happy_path(api_client, cache_db, monkeypatch):
    """AJAX bind: valid token + known order → ok=true."""
    client, conn = api_client
    monkeypatch.setenv("CRM_CACHE_DB", cache_db)
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)  # skip D1 push
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ajax-bind")
    resp = client.post("/hug/claim/bind", json={
        "session_id": "sess-ajax-1",
        "token": tok,
        "fields": {"order_code": "SO1234", "is_gift": False},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


@_api_only
def test_bind_ajax_amber_order_still_allowed(api_client, cache_db, monkeypatch):
    """AJAX bind: order not in cache (amber/unknown) → still allowed (soft-fail)."""
    client, conn = api_client
    monkeypatch.setenv("CRM_CACHE_DB", cache_db)
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ajax-amber")
    resp = client.post("/hug/claim/bind", json={
        "session_id": "sess-ajax-2",
        "token": tok,
        "fields": {"order_code": "SO9999", "is_gift": False},
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True  # amber → proceed


@_api_only
def test_bind_ajax_missing_required_field(api_client, monkeypatch):
    client, conn = api_client
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ajax-missing")
    resp = client.post("/hug/claim/bind", json={
        "session_id": "sess-ajax-3",
        "token": tok,
        "fields": {"is_gift": False},  # missing order_code (required)
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


@_api_only
def test_bind_ajax_invalid_token(api_client):
    client, _ = api_client
    resp = client.post("/hug/claim/bind", json={
        "session_id": "s",
        "token": "TOOSHORT",
        "fields": {"order_code": "SO1"},
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is False


@_api_only
def test_bind_ajax_different_session_blocked(api_client, cache_db, monkeypatch):
    """AJAX bind: token already bound to sess-A, request uses sess-B → ok=false."""
    client, conn = api_client
    monkeypatch.setenv("CRM_CACHE_DB", cache_db)
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)
    [tok] = repository.mint_batch(conn, 1, batch_id="B-ajax-cross")
    # First bind with session A
    repository.bind_token(conn, tok, order_code="SO1234", bind_session_id="sess-A")
    # Attempt bind from session B
    resp = client.post("/hug/claim/bind", json={
        "session_id": "sess-B",
        "token": tok,
        "fields": {"order_code": "SO1234", "is_gift": False},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "different operation" in data["message"]


@_api_only
def test_existing_form_post_still_works(api_client, cache_db, monkeypatch):
    """no-JS form POST unchanged — must render HTML success page."""
    client, conn = api_client
    monkeypatch.delenv("HUG_WORKER_URL", raising=False)
    [tok] = repository.mint_batch(conn, 1, batch_id="B-form-compat")
    resp = client.post("/hug/claim", data={
        "token": tok,
        "order_code": "SO1234",
        "is_gift": "",
    })
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "✓" in resp.text  # success icon in HTML


# ── 8. bind_attributes in D1 payload (pre-Phase 4: attributes not yet pushed) ─

def test_bind_attributes_not_exposed_in_d1_payload(hug_conn):
    """Phase 4 will add attributes to the D1 push payload; until then it must not appear."""
    from hug import d1_push
    [tok] = repository.mint_batch(hug_conn, 1, batch_id="B-d1-attrs")
    row = repository.bind_token(
        hug_conn, tok,
        order_code="SO5",
        bind_attributes={"note": "test"},
    )
    payload = d1_push._row_to_payload(row)
    assert "bind_attributes" not in payload
    assert "attributes" not in payload


# ── 9. Phase 3: _render_page config-driven output ────────────────────────────

try:
    # _render_page is a pure function; FastAPI is only needed for the router.
    # Import screen_hug_claim only when FastAPI is available (it imports APIRouter at module level).
    if _FASTAPI_AVAILABLE:
        from adapters.inbound.web.screen_hug_claim import _render_page as _rp  # noqa: E402
        _RENDER_PAGE_AVAILABLE = True
    else:
        _RENDER_PAGE_AVAILABLE = False
except ImportError:
    _RENDER_PAGE_AVAILABLE = False

_render_only = pytest.mark.skipif(
    not _RENDER_PAGE_AVAILABLE,
    reason="_render_page not importable (FastAPI not installed in this environment)",
)


@_render_only
def test_render_page_contains_session_id_declaration():
    """JS block must declare SESSION_ID via crypto.randomUUID()."""
    html = _rp()
    assert "SESSION_ID" in html
    assert "crypto.randomUUID()" in html


@_render_only
def test_render_page_contains_bind_endpoint():
    """AJAX bind endpoint path must be embedded in the rendered page."""
    html = _rp()
    assert "/hug/claim/bind" in html


@_render_only
def test_render_page_contains_check_token_endpoint():
    """Token live-check endpoint path must be embedded."""
    html = _rp()
    assert "check-token" in html


@_render_only
def test_render_page_contains_check_field_endpoint():
    """Per-field live-check endpoint path must be embedded."""
    html = _rp()
    assert "check-field" in html


@_render_only
def test_render_page_has_order_code_input():
    """Config-driven render must produce id='f_order_code' input."""
    html = _rp()
    assert 'id="f_order_code"' in html


@_render_only
def test_render_page_has_is_gift_input():
    """Config-driven render must produce id='f_is_gift' checkbox."""
    html = _rp()
    assert 'id="f_is_gift"' in html


@_render_only
def test_render_page_has_token_input_with_f_prefix():
    """Token input must use id='f_token' to match getFieldEl('token')."""
    html = _rp()
    assert 'id="f_token"' in html


@_render_only
def test_render_page_prefills_order_code():
    """When order_code param given, the input value must reflect it."""
    html = _rp(order_code="SO9876")
    assert 'value="SO9876"' in html


@_render_only
def test_render_page_embeds_claim_fields_as_valid_json():
    """FIELDS constant in <script> must be parseable JSON containing CLAIM_FIELDS keys."""
    import re
    page = _rp()
    # Extract the FIELDS = ...; assignment from the script block
    match = re.search(r'const FIELDS = (\[.*?\]);', page, re.DOTALL)
    assert match, "const FIELDS = [...] not found in rendered HTML"
    parsed = json.loads(match.group(1))
    keys = [f["key"] for f in parsed]
    assert "order_code" in keys
    assert "is_gift" in keys


@_render_only
def test_render_page_claim_fields_json_strips_validate():
    """Frontend FIELDS JSON must not expose the 'validate' backend key."""
    import re
    page = _rp()
    match = re.search(r'const FIELDS = (\[.*?\]);', page, re.DOTALL)
    assert match
    parsed = json.loads(match.group(1))
    for field in parsed:
        assert "validate" not in field


@_render_only
def test_render_page_no_js_form_present():
    """No-JS fallback: <form method='post' action='/hug/claim'> must remain."""
    html = _rp()
    assert 'method="post"' in html
    assert 'action="/hug/claim"' in html


@_render_only
def test_render_page_result_div_present():
    """result div with id='result' must be present for AJAX updates."""
    html = _rp()
    assert 'id="result"' in html


@_render_only
def test_render_page_syntax_warning_clean():
    """Module must import with -W error::SyntaxWarning (no invalid escapes)."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-W", "error::SyntaxWarning", "-c",
         "from adapters.inbound.web.screen_hug_claim import _render_page"],
        capture_output=True, text=True,
        cwd=str(pathlib.Path(__file__).parents[1]),
    )
    assert result.returncode == 0, f"SyntaxWarning raised:\n{result.stderr}"
