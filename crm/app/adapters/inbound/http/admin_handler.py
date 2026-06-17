"""admin_handler.py — FastAPI router for POST /admin/refresh and GET /admin/status.

Mirrors Go AdminHandler behaviour (admin_handler.go):
  - Single-flight: only one refresh runs at a time; second caller gets 409.
  - Auth: if CRM_REFRESH_TOKEN env is set, X-Refresh-Token header must match.
  - Fire-and-forget: POST returns 202 immediately; asyncio background task runs
    reverse_etl then sync_parties sequentially.
  - GET /admin/status: returns last-run state (idle | running | ok | error).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

_REFRESH_TIMEOUT_S = 15 * 60  # 15-minute safety cap — matches Go defaultRefreshTimeout


def _sync_parties_run() -> None:
    """Run sync_parties inline without invoking argparse (safe for programmatic call)."""
    import os as _os
    data_dir = _os.environ.get("CRM_DATA_DIR", "./data")

    # Imports are relative to crm/app/ on sys.path (set by the server entrypoint).
    from adapters.outbound.sqlite.connection import CRMDatabase
    from adapters.outbound.sqlite.party_repository import SQLitePartyRepository
    from adapters.outbound.sqlite.cache_repository import SQLiteCacheRepository
    from application.party_seed_service import PartySeedService

    db = CRMDatabase(data_dir)
    try:
        db.apply_migrations()
        party_repo = SQLitePartyRepository(db.conn)
        cache_repo = SQLiteCacheRepository(db.conn)
        svc = PartySeedService(cache_repo, party_repo)
        n = svc.sync_parties(cache_repo)
        log.info("syncparties: %d parties upserted", n)
    finally:
        db.close()


def _reverse_etl_run() -> None:
    """Run reverse_etl from the crm.sync package (importable from repo root)."""
    from crm.sync import reverse_etl_warehouse_to_crm
    reverse_etl_warehouse_to_crm.run()


def create_admin_router() -> APIRouter:
    """Return the admin router.  Token is read from CRM_REFRESH_TOKEN at request time."""
    r = APIRouter()

    # Use a dict as a mutable container so closures can mutate state reliably.
    _state: dict[str, Any] = {"status": "idle", "last_run": None}
    _guard: dict[str, bool] = {"running": False}
    _lock = asyncio.Lock()

    async def _run_refresh(started_at: datetime) -> None:
        """Background task: reverse_etl → sync_parties.  Clears running flag on exit."""
        iso_start = started_at.isoformat()
        loop = asyncio.get_event_loop()
        try:
            log.info("admin: reverse_etl starting")
            await asyncio.wait_for(
                loop.run_in_executor(None, _reverse_etl_run),
                timeout=_REFRESH_TIMEOUT_S,
            )
            log.info("admin: sync_parties starting")
            await asyncio.wait_for(
                loop.run_in_executor(None, _sync_parties_run),
                timeout=_REFRESH_TIMEOUT_S,
            )
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            log.info("admin: refresh ok in %dms", duration_ms)
            _state.update({
                "status": "ok",
                "last_run": {
                    "started_at": iso_start,
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": duration_ms,
                    "error": None,
                },
            })
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            log.error("admin: refresh failed after %dms: %s", duration_ms, exc)
            _state.update({
                "status": "error",
                "last_run": {
                    "started_at": iso_start,
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            })
        finally:
            async with _lock:
                _guard["running"] = False

    @r.post("/admin/refresh")
    async def post_refresh(
        x_refresh_token: str | None = Header(default=None),
    ) -> JSONResponse:
        token = os.environ.get("CRM_REFRESH_TOKEN", "")
        if token and x_refresh_token != token:
            raise HTTPException(status_code=401, detail={"status": "unauthorized"})
        if not token:
            log.warning("admin: CRM_REFRESH_TOKEN unset — /admin/refresh is UNPROTECTED (LAN-trust only)")

        async with _lock:
            if _guard["running"]:
                return JSONResponse(status_code=409, content={"status": "already_running"})
            _guard["running"] = True
            started_at = datetime.now(timezone.utc)
            _state.update({"status": "running", "last_run": {"started_at": started_at.isoformat()}})

        asyncio.create_task(_run_refresh(started_at))
        log.info("admin: refresh accepted (running async)")
        return JSONResponse(
            status_code=202,
            content={"status": "accepted", "started_at": started_at.isoformat()},
        )

    @r.get("/admin/status")
    async def get_status() -> JSONResponse:
        # Read-only; no token required so ops/Dagster can poll freely.
        return JSONResponse(status_code=200, content=dict(_state))

    return r
