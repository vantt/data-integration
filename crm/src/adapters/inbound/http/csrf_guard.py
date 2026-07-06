"""csrf_guard.py — Starlette middleware: reject/log cross-origin state-changing requests.

CF Access (see cf_access_middleware.py) made CRM internet-facing with real per-user
sessions, which turns CSRF from a theoretical LAN-only risk into a real one: a malicious
page can trick a logged-in browser into POSTing to crm.fwg.vn and the CF Access cookie
rides along automatically.

Mechanism: compare the Origin (or Referer) header's host against the request's own Host
header. No domain allowlist to maintain — whatever host the browser used to reach the app
IS the expected origin, whether that's crm.fwg.vn, crm.lan.fwg.vn, or local dev.

This works uniformly whether the mutating form is HTMX (`hx-post`, sends `HX-Request`) or a
plain `<form method="post">` — the /hug/* screens use plain forms with no hx-post at all, so
a header-only `HX-Request` guard would 403 all of them.

/api/* is exempt — those routes carry their own auth (CRM_API_TOKEN / webhook HMAC, see
auth_dependency.py), are called server-to-server, and legitimately have no browser Origin.

CRM_CSRF_ENFORCE=false (default): log-only — mismatches are logged, not blocked. Flip to
"true" once a rollout cycle confirms no legitimate caller is flagged.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger(__name__)

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _csrf_enforce() -> bool:
    return os.environ.get("CRM_CSRF_ENFORCE", "false").strip().lower() in ("1", "true", "yes")


def _host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except ValueError:
        return ""


class CSRFGuardMiddleware(BaseHTTPMiddleware):
    """Block (or log, during rollout) state-changing requests whose Origin/Referer host
    doesn't match the request's own Host header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _MUTATING_METHODS or request.url.path.startswith("/api/"):
            return await call_next(request)

        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")
        source_host = _host_of(origin) if origin else _host_of(referer)

        if not source_host:
            # No Origin/Referer at all — ambiguous (non-browser caller, or a browser that
            # stripped both). OWASP guidance: log, don't block on absence alone.
            log.debug(
                "csrf_guard: %s %s has no Origin/Referer header", request.method, request.url.path
            )
            return await call_next(request)

        request_host = request.headers.get("host", "").lower()
        if source_host == request_host:
            return await call_next(request)

        message = (
            f"csrf_guard: cross-origin {request.method} {request.url.path} "
            f"(source={source_host!r} host={request_host!r})"
        )
        if _csrf_enforce():
            log.warning("%s — BLOCKED", message)
            return Response("Forbidden — cross-origin request rejected", status_code=403)

        log.warning("%s — would block (CRM_CSRF_ENFORCE=false, log-only)", message)
        return await call_next(request)
