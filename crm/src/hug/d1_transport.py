"""d1_transport.py — shared HMAC-signed HTTP transport for Hug → Worker pushes.

All Hug admin upsert routes share the same auth scheme:
  X-Hug-Signature: sha256=<hex(hmac_sha256(HUG_ADMIN_SECRET, raw_body))>

An explicit User-Agent is mandatory: Cloudflare Bot Fight Mode rejects the
default "Python-urllib/x.y" agent on the proxied Worker domains (error 1010).

This module is the single implementation.  d1_push (token push) and
customer_push both import from here — no duplication of signing logic.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger(__name__)

_TIMEOUT_S = 8
_USER_AGENT = "FineJapan-Hug-Push/1.0"


def sign(secret: str, raw_body: bytes) -> str:
    """Return the HMAC-SHA256 hex signature in ``sha256=<hex>`` format."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def post_signed(
    url: str,
    secret: str,
    payload: dict[str, Any],
    *,
    timeout_s: int = _TIMEOUT_S,
) -> dict[str, Any]:
    """POST *payload* as JSON to *url* with HMAC signature + explicit User-Agent.

    Returns a result dict:
      {"ok": True,  "status": <http_int>}                 — success
      {"ok": False, "error": <str>}                       — HTTP or network failure

    Never raises — callers are fire-and-forget pushes where local state is
    already committed.
    """
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=raw_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Hug-Signature": sign(secret, raw_body),
            # Cloudflare Bot Fight Mode rejects the default Python-urllib UA
            # with a silent 403 (error 1010); an explicit UA passes through.
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return {"ok": True, "status": resp.status}
    except urllib.error.HTTPError as exc:
        log.error("hug push: HTTP %d at %s — %s", exc.code, url, exc.reason)
        return {"ok": False, "error": f"http {exc.code}"}
    except Exception as exc:  # network/timeout — retryable later
        log.error("hug push: failed at %s — %s", url, exc)
        return {"ok": False, "error": str(exc)}
