"""test_hug_d1_transport.py — unit tests for post_signed_and_read in d1_transport.py.

Tests do NOT make real HTTP calls — they mock urllib.request.urlopen to simulate
various server responses. post_signed_and_read must never raise.

Coverage:
  T01  success: HTTP 200, valid JSON body → {"ok": True, "status": 200, "data": ...}
  T02  HTTP error (401) → {"ok": False, "error": "http 401"}
  T03  network error (timeout) → {"ok": False, "error": <str>}
  T04  success HTTP status but invalid JSON body → {"ok": False, "error": "invalid json: ..."}
  T05  never raises — even on unexpected exception inside handler
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import urllib.error
from http.client import HTTPMessage
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure crm/src is importable without package install.
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hug.d1_transport import post_signed_and_read  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Minimal context-manager response mock for urllib.request.urlopen."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass


def _make_http_error(code: int, reason: str = "Error") -> urllib.error.HTTPError:
    """Build a urllib.error.HTTPError whose .read() returns an empty body."""
    err = urllib.error.HTTPError(
        url="http://example.com",
        code=code,
        msg=reason,
        hdrs=HTTPMessage(),  # type: ignore[arg-type]
        fp=io.BytesIO(b""),
    )
    return err


# ---------------------------------------------------------------------------
# T01 — success: valid JSON response
# ---------------------------------------------------------------------------

def test_T01_success_returns_parsed_json():
    """T01: HTTP 200 with valid JSON → ok=True, status=200, data parsed."""
    payload = {"worker": "response", "count": 42}
    fake_resp = _FakeResponse(json.dumps(payload).encode())

    with patch("hug.d1_transport.urllib.request.urlopen", return_value=fake_resp):
        result = post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="testsecret",
            payload={"targeting": {}, "limit": 50, "offset": 0},
        )

    assert result["ok"] is True
    assert result["status"] == 200
    assert result["data"] == payload


# ---------------------------------------------------------------------------
# T02 — HTTP error
# ---------------------------------------------------------------------------

def test_T02_http_error_returns_ok_false():
    """T02: HTTP 401 → ok=False, error="http 401"."""
    with patch(
        "hug.d1_transport.urllib.request.urlopen",
        side_effect=_make_http_error(401),
    ):
        result = post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="testsecret",
            payload={"targeting": {}},
        )

    assert result["ok"] is False
    assert "401" in result["error"]


# ---------------------------------------------------------------------------
# T03 — network/timeout error
# ---------------------------------------------------------------------------

def test_T03_network_error_returns_ok_false_never_raises():
    """T03: network timeout → ok=False, error contains message, no raise."""
    with patch(
        "hug.d1_transport.urllib.request.urlopen",
        side_effect=TimeoutError("connection timed out"),
    ):
        result = post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="testsecret",
            payload={"targeting": {}},
        )

    assert result["ok"] is False
    assert result["error"]  # non-empty string


# ---------------------------------------------------------------------------
# T04 — valid HTTP status but response is not JSON
# ---------------------------------------------------------------------------

def test_T04_invalid_json_response_returns_ok_false():
    """T04: 200 but body is not JSON → ok=False, error starts with 'invalid json'."""
    fake_resp = _FakeResponse(b"<html>not json</html>")

    with patch("hug.d1_transport.urllib.request.urlopen", return_value=fake_resp):
        result = post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="testsecret",
            payload={"targeting": {}},
        )

    assert result["ok"] is False
    assert result["error"].startswith("invalid json")


# ---------------------------------------------------------------------------
# T05 — never raises under any circumstance
# ---------------------------------------------------------------------------

def test_T05_never_raises_on_unexpected_exception():
    """T05: any unexpected exception → ok=False, no raise."""
    with patch(
        "hug.d1_transport.urllib.request.urlopen",
        side_effect=RuntimeError("unexpected internal error"),
    ):
        result = post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="testsecret",
            payload={"targeting": {}},
        )

    assert result["ok"] is False
    assert "unexpected internal error" in result["error"]


# ---------------------------------------------------------------------------
# T06 — request body is signed (HMAC header present and non-empty)
# ---------------------------------------------------------------------------

def test_T06_request_includes_hmac_signature():
    """T06: the signed request must include X-Hug-Signature header with sha256= prefix."""
    captured_headers: dict[str, Any] = {}
    fake_resp = _FakeResponse(json.dumps({"ok": True}).encode())

    original_request_init = None

    import urllib.request as _urllib_request

    class _CapturingRequest(_urllib_request.Request):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            captured_headers.update(dict(self.headers))

    with (
        patch("hug.d1_transport.urllib.request.Request", _CapturingRequest),
        patch("hug.d1_transport.urllib.request.urlopen", return_value=fake_resp),
    ):
        post_signed_and_read(
            "http://worker.example.com/hug/campaign/preview",
            secret="secret123",
            payload={"targeting": {"tier": ["VIP"]}},
        )

    # Header names are title-cased by urllib.request.Request
    sig = captured_headers.get("X-hug-signature", "")
    assert sig.startswith("sha256="), f"Expected sha256= prefix, got: {sig!r}"
