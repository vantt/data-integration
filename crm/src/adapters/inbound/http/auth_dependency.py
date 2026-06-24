"""auth_dependency.py — Shared FastAPI dependency for mutation-API token auth.

Guards all /api/* mutation routes (POST/PATCH/PUT/DELETE) against unauthenticated
callers.  Read-only GET routes and the web UI (HTMX at unprefixed paths) are NOT
affected.

Token: X-CRM-Token header must match CRM_API_TOKEN env var.
Backward-compatible: if CRM_API_TOKEN is unset, auth is BYPASSED with a warning
(same pattern as CRM_REFRESH_TOKEN on /admin/refresh) so a rebuilt container
without the env var continues to work until it is configured.

Excluded routes (caller supplies its own auth or is external):
  POST /api/conversations/messenger/ingest — FB Messenger webhook (FB signs with
    X-Hub-Signature-256; adding CRM_API_TOKEN would block Facebook's server).
"""
from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException

log = logging.getLogger(__name__)


def require_api_token(
    x_crm_token: str | None = Header(default=None),
) -> None:
    """FastAPI dependency: enforce CRM_API_TOKEN on mutation routes.

    Usage::

        router = APIRouter(dependencies=[Depends(require_api_token)])

    Behaviour:
      - CRM_API_TOKEN set + header matches  → allowed
      - CRM_API_TOKEN set + header missing/wrong → 401
      - CRM_API_TOKEN unset                → allowed (warn once per process)
    """
    token = os.environ.get("CRM_API_TOKEN", "")
    if not token:
        # Warn once per process rather than spamming every request.
        if not getattr(require_api_token, "_warned", False):
            log.warning(
                "CRM_API_TOKEN unset — /api/* mutation routes are UNPROTECTED "
                "(LAN-trust only; set CRM_API_TOKEN to enable token auth)"
            )
            require_api_token._warned = True  # type: ignore[attr-defined]
        return
    if x_crm_token != token:
        raise HTTPException(status_code=401, detail={"status": "unauthorized"})
