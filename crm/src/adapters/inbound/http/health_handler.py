"""health_handler.py — FastAPI router for GET /healthz.

Returns 200 {"status":"ok"} when crm.db is reachable and cache schema is
attached; 503 {"status":"degraded"} otherwise. Mirrors Go HealthHandler
behaviour (health_handler.go).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

router = APIRouter()

# Module-level db reference — set by create_health_router() below.
# Using a factory keeps the interface testable (inject any HealthChecker duck-type).
_db = None


def create_health_router(db) -> APIRouter:
    """Return the router bound to *db*.

    *db* must expose:
      - ping() -> None  (raises on failure)
      - cache_attached() -> bool
    """
    r = APIRouter()

    @r.get("/healthz")
    async def healthz() -> JSONResponse:
        crm_ok = False
        try:
            db.ping()
            crm_ok = True
        except Exception as exc:
            log.warning("health: db.ping() failed: %s", exc)

        cache_ok: bool = False
        try:
            cache_ok = db.cache_attached()
        except Exception as exc:
            log.warning("health: db.cache_attached() failed: %s", exc)

        status = "ok" if (crm_ok and cache_ok) else "degraded"
        code = 200 if status == "ok" else 503
        return JSONResponse(
            status_code=code,
            content={
                "status": status,
                "db": "ok" if crm_ok else "error",
                "cache": cache_ok,
            },
        )

    return r
