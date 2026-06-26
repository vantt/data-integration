"""cf_access_middleware.py — Starlette middleware: verify Cloudflare Access JWT.

Injects request.state.current_user: Optional[AppUser] on every request.
If CF_ACCESS_AUDIENCE is unset → bypass (dev/LAN mode, current_user = None).

JWT verification:
  - Fetches JWKS once from https://<CF_TEAM_DOMAIN>/cdn-cgi/access/certs
  - Caches keys in memory for the process lifetime (restart refreshes)
  - RS256 only — CF Access always signs with RS256
  - Validates aud claim against CF_ACCESS_AUDIENCE

Role mapping:
  - Reads Lark role from JWT at path CF_ROLE_CLAIM (dot-separated: "custom.role")
  - Maps to CRM role via CF_ROLE_MAP dict
  - Falls back to "sales" if unmapped
"""
from __future__ import annotations

import json
import logging
import urllib.request

import jwt  # PyJWT
from jwt.algorithms import RSAAlgorithm
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from application.app_user_service import AppUserService
from config import cf_access_audience, cf_team_domain, cf_role_claim, cf_role_map

log = logging.getLogger(__name__)

# Module-level JWKS cache: kid → public key object (populated on first verified request).
_JWKS_CACHE: dict[str, object] = {}


def _fetch_jwks(team_domain: str) -> dict[str, object]:
    global _JWKS_CACHE
    if _JWKS_CACHE:
        return _JWKS_CACHE
    url = f"https://{team_domain}/cdn-cgi/access/certs"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())
    for key_data in data.get("keys", []):
        kid = key_data.get("kid")
        if kid:
            _JWKS_CACHE[kid] = RSAAlgorithm.from_jwk(json.dumps(key_data))
    log.info("CF Access JWKS loaded: %d key(s)", len(_JWKS_CACHE))
    return _JWKS_CACHE


def _get_claim(payload: dict, path: str) -> str:
    """Read a dot-separated claim path from JWT payload. E.g. 'custom.role'."""
    parts = path.split(".")
    val = payload
    for p in parts:
        if not isinstance(val, dict):
            return ""
        val = val.get(p, "")
    return str(val) if val else ""


def _name_from_email(email: str) -> str:
    """Derive a display name from email prefix when IDP doesn't forward name.

    van.tran@example.com  →  Van Tran
    john_doe@example.com  →  John Doe
    """
    prefix = email.split("@")[0]
    parts = prefix.replace(".", " ").replace("_", " ").replace("-", " ").split()
    return " ".join(p.capitalize() for p in parts) if parts else email


class CFAccessMiddleware(BaseHTTPMiddleware):
    """Verify CF Access JWT and inject request.state.current_user."""

    def __init__(self, app, user_svc: AppUserService) -> None:
        super().__init__(app)
        self._user_svc = user_svc
        self._audience = cf_access_audience()
        self._team_domain = cf_team_domain()
        self._role_claim = cf_role_claim()
        self._role_map: dict[str, str] = cf_role_map()

        if not self._audience:
            log.warning(
                "CF_ACCESS_AUDIENCE unset — auth BYPASSED (LAN/dev mode). "
                "Set it to enable Cloudflare Access protection."
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.current_user = None

        if not self._audience:
            # Bypass: dev/LAN mode
            return await call_next(request)

        token = request.headers.get("Cf-Access-Jwt-Assertion", "")
        if not token:
            # No JWT — CF Access should have blocked this; pass through
            # (healthz, static files, etc. don't need a user)
            return await call_next(request)

        try:
            jwks = _fetch_jwks(self._team_domain)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid", "")
            pub_key = jwks.get(kid)
            if pub_key is None:
                log.warning("CF Access JWT: unknown kid=%r", kid)
                return Response("Unauthorized", status_code=401)

            payload = jwt.decode(
                token,
                pub_key,
                algorithms=["RS256"],
                audience=self._audience,
            )
        except jwt.ExpiredSignatureError:
            return Response("Token expired", status_code=401)
        except Exception:
            log.exception("CF Access JWT verification failed")
            return Response("Unauthorized", status_code=401)

        email: str = payload.get("email", "")
        raw_name: str = payload.get("name", "")
        # CF Access email-OTP doesn't forward name; derive from email prefix.
        name: str = raw_name or _name_from_email(email)
        lark_role: str = _get_claim(payload, self._role_claim)
        crm_role: str = self._role_map.get(lark_role, "sales")

        try:
            user = self._user_svc.provision_or_sync(email, name, crm_role)
            request.state.current_user = user
        except Exception:
            log.exception("user provisioning failed for %s", email)

        return await call_next(request)
