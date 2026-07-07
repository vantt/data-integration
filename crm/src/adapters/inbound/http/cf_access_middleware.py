"""cf_access_middleware.py — Starlette middleware: verify Cloudflare Access JWT.

Injects request.state.current_user: Optional[AppUser] on every request.
If CF_ACCESS_AUDIENCE is unset → bypass (dev/LAN mode, current_user = None).

JWT verification:
  - Fetches JWKS once from https://<CF_TEAM_DOMAIN>/cdn-cgi/access/certs
  - Caches keys in memory for the process lifetime (restart refreshes)
  - RS256 only — CF Access always signs with RS256
  - Validates aud claim against CF_ACCESS_AUDIENCE

Name resolution:
  - CF Access JWT contains no "name" claim (email-OTP IDP)
  - Fallback: derive from email prefix (van.tran@ → "Van Tran")
  - Real name is synced later via client-side JS calling /profile/sync
    (browser fetches /cdn-cgi/access/identity and POSTs idp_claims.name)

Role mapping:
  - Reads Lark departments/functional_roles from JWT at CF_DEPT_CLAIM /
    CF_FUNC_ROLE_CLAIM (dot-separated, e.g. "custom.departments") — both
    are arrays since a user can belong to several departments/roles.
  - Every value is looked up in CF_ROLE_MAP; a value starting with a
    CF_MANAGER_PREFIXES prefix (default "truong-phong-", "head-of-") maps to
    manager regardless of CF_ROLE_MAP — head-of-department combos aren't
    enumerable one entry per department.
  - When several values map to different CRM roles, the highest-privilege
    one wins (admin > manager > care > sales) so a user with any
    admin/manager membership keeps it.
  - Falls back to "sales" if nothing matches.

Admin bootstrap:
  - CRM_ADMIN_EMAILS (comma-separated) forces role=admin on FIRST provision
    only; existing users are never auto-elevated (warn instead — change
    role via Settings UI).
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
from domain.entities.app_user import ROLE_ADMIN, ROLE_CARE, ROLE_MANAGER, ROLE_SALES
from config import (
    cf_access_audience,
    cf_admin_emails,
    cf_dept_claim,
    cf_func_role_claim,
    cf_manager_prefixes,
    cf_role_map,
    cf_team_domain,
)

log = logging.getLogger(__name__)

# Highest-privilege role wins when several departments/functional_roles match.
_ROLE_PRIORITY = (ROLE_ADMIN, ROLE_MANAGER, ROLE_CARE, ROLE_SALES)

# JWKS cache: kid → public key (process lifetime)
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


def _get_claim_values(payload: dict, path: str) -> list[str]:
    """Read a dot-separated claim path from JWT payload; always returns a list.

    Lark departments/functional_roles are arrays, but tolerate a single
    scalar value too (manual test tokens, or a claim not yet array-shaped).
    """
    parts = path.split(".")
    val = payload
    for p in parts:
        if not isinstance(val, dict):
            return []
        val = val.get(p)
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if val:
        return [str(val)]
    return []


def _resolve_crm_role(claim_values: list[str], role_map: dict, manager_prefixes: tuple = ()) -> str:
    """Map department/functional_role claim values to a CRM role.

    A user can carry several departments/functional roles; when they map to
    different CRM roles the highest-privilege match wins. A value starting
    with a manager_prefixes entry (e.g. "truong-phong-tai-chinh") always
    counts as manager — head-of-department combos aren't enumerable one by
    one in role_map. Falls back to ROLE_SALES when nothing matches.
    """
    matched = {role_map[v] for v in claim_values if v in role_map}
    if manager_prefixes and any(v.startswith(manager_prefixes) for v in claim_values):
        matched.add(ROLE_MANAGER)
    for role in _ROLE_PRIORITY:
        if role in matched:
            return role
    return ROLE_SALES


def _name_from_email(email: str) -> str:
    """Derive a display name from email prefix (fallback until JS syncs real name).

    van.tran@example.com  →  Van Tran
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
        self._dept_claim = cf_dept_claim()
        self._func_role_claim = cf_func_role_claim()
        self._role_map: dict = cf_role_map()
        self._manager_prefixes: tuple = cf_manager_prefixes()
        self._admin_emails: set = cf_admin_emails()

        if not self._audience:
            log.warning(
                "CF_ACCESS_AUDIENCE unset — auth BYPASSED (LAN/dev mode). "
                "Set it to enable Cloudflare Access protection."
            )

    def _compute_initial_role(self, email: str, claim_values: list[str]) -> str:
        """CRM role to pass into provision_or_sync for this email.

        CRM_ADMIN_EMAILS wins over the claim-derived role, but only for an
        email that has never provisioned before (no auto-elevation of
        existing users — see module docstring).
        """
        crm_role = _resolve_crm_role(claim_values, self._role_map, self._manager_prefixes)
        if email.lower() in self._admin_emails and not self._user_svc.is_registered(email):
            crm_role = ROLE_ADMIN
        return crm_role

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.current_user = None

        if not self._audience:
            return await call_next(request)

        token = request.headers.get("Cf-Access-Jwt-Assertion", "")
        if not token:
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
        custom: dict = payload.get("custom") or {}
        name: str = custom.get("name") or payload.get("name") or _name_from_email(email)
        lark_user_id: str = custom.get("sub") or ""   # Lark open_id via custom.sub claim

        claim_values = (
            _get_claim_values(payload, self._dept_claim)
            + _get_claim_values(payload, self._func_role_claim)
        )
        crm_role = self._compute_initial_role(email, claim_values)

        try:
            user = self._user_svc.provision_or_sync(email, name, crm_role, lark_user_id=lark_user_id)
            request.state.current_user = user
            if email.lower() in self._admin_emails and user.role != ROLE_ADMIN:
                log.warning(
                    "email %s is in CRM_ADMIN_EMAILS but current role is %r "
                    "(bootstrap only applies on first login — change via Settings UI)",
                    email, user.role,
                )
        except Exception:
            log.exception("user provisioning failed for %s", email)

        return await call_next(request)
