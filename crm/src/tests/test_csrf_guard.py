"""test_csrf_guard.py — Unit tests for CSRFGuardMiddleware.

Cases:
  - same_origin_post: Origin host == Host header -> allowed
  - cross_origin_post_enforce: Origin host != Host, CRM_CSRF_ENFORCE=true -> 403
  - cross_origin_post_log_only: Origin host != Host, CRM_CSRF_ENFORCE unset -> allowed (log-only)
  - referer_fallback: no Origin, Referer host == Host -> allowed
  - missing_both: no Origin, no Referer -> allowed (ambiguous, never block on absence alone)
  - api_prefix_exempt: /api/* mutation with mismatched Origin -> allowed regardless of enforce
  - get_request_untouched: GET with mismatched Origin -> allowed (not a mutating method)

Tests call CSRFGuardMiddleware.dispatch() directly against a bare Starlette Request built
from a minimal ASGI scope, instead of spinning up a FastAPI app + TestClient — a true unit
test of the guard's own logic, independent of routing/app wiring. This also sidesteps
pytest-asyncio (not a project dependency): async dispatch() is driven with asyncio.run(),
matching the existing convention in test_bulk_resolve_endpoint.py.

Run:
  PYTHONPATH="crm/src" python -m pytest crm/src/tests/test_csrf_guard.py -q
"""
from __future__ import annotations

import asyncio
import pathlib
import sys

import pytest
from starlette.requests import Request
from starlette.responses import Response

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from adapters.inbound.http.csrf_guard import CSRFGuardMiddleware  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_request(method: str, path: str, headers: dict[str, str]) -> Request:
    """Build a bare Starlette Request from a minimal ASGI scope (no ASGI app, no I/O)."""
    encoded_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": encoded_headers,
        "query_string": b"",
    }
    return Request(scope)


async def _call_next_ok(_request: Request) -> Response:
    return Response("ok", status_code=200)


def _dispatch(method: str, path: str, headers: dict[str, str]) -> Response:
    guard = CSRFGuardMiddleware(app=None)  # app unused — dispatch() is invoked directly
    request = _make_request(method, path, headers)
    return asyncio.run(guard.dispatch(request, _call_next_ok))


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_same_origin_post_allowed() -> None:
    resp = _dispatch("POST", "/mutate", {"Origin": "https://crm.fwg.vn", "Host": "crm.fwg.vn"})
    assert resp.status_code == 200


def test_cross_origin_post_blocked_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRM_CSRF_ENFORCE", "true")
    resp = _dispatch("POST", "/mutate", {"Origin": "https://evil.example", "Host": "crm.fwg.vn"})
    assert resp.status_code == 403


def test_cross_origin_post_logged_not_blocked_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRM_CSRF_ENFORCE", raising=False)
    resp = _dispatch("POST", "/mutate", {"Origin": "https://evil.example", "Host": "crm.fwg.vn"})
    assert resp.status_code == 200


def test_referer_fallback_allowed() -> None:
    resp = _dispatch("POST", "/mutate", {"Referer": "https://crm.fwg.vn/tasks/1", "Host": "crm.fwg.vn"})
    assert resp.status_code == 200


def test_missing_origin_and_referer_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRM_CSRF_ENFORCE", "true")
    resp = _dispatch("POST", "/mutate", {"Host": "crm.fwg.vn"})
    assert resp.status_code == 200


def test_api_prefix_exempt_even_when_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRM_CSRF_ENFORCE", "true")
    resp = _dispatch("POST", "/api/sync", {"Origin": "https://evil.example", "Host": "crm.fwg.vn"})
    assert resp.status_code == 200


def test_get_request_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRM_CSRF_ENFORCE", "true")
    resp = _dispatch("GET", "/mutate", {"Origin": "https://evil.example", "Host": "crm.fwg.vn"})
    assert resp.status_code == 200
