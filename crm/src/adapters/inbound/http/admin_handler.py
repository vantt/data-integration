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

    # Imports are relative to crm/src/ on sys.path (set by the server entrypoint).
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


def _hug_resolve_run() -> None:
    """Resolve new Hug opt-in events into crm_identity_link (identity bridge).

    Runs AFTER reverse_etl (so cache.wh_order_hdr is fresh for order→customer
    lookup) and BEFORE the customer push (so newly-linked customers show as
    contactable in the same refresh). Reads mart_hug_optin from olap.duckdb
    (read-only) + crm.db + hug.db. Skips cleanly when olap.duckdb is absent
    (pre-deploy) so it never aborts the refresh.
    """
    import os as _os
    import pathlib
    import sqlite3

    from crm.sync.config import cache_db_path, olap_path
    from hug import config as hug_config
    from hug.identity_resolver import resolve_new_optins

    olap = olap_path()
    if not _os.path.exists(olap):
        log.info("hug_resolve: olap.duckdb not found at %s — skipping (pre-deploy)", olap)
        return

    data_dir = _os.environ.get("CRM_DATA_DIR", "./data")
    crm_db = str(pathlib.Path(data_dir) / "crm.db")
    watermark = str(pathlib.Path(data_dir) / "hug_resolver_watermark.json")

    crm_conn = sqlite3.connect(crm_db)
    crm_conn.row_factory = sqlite3.Row
    hug_conn = sqlite3.connect(hug_config.hug_db_path())
    hug_conn.row_factory = sqlite3.Row
    try:
        # The resolver reads order→customer from cache.wh_order_hdr.
        crm_conn.execute("ATTACH DATABASE ? AS cache", (cache_db_path(),))
        n = resolve_new_optins(crm_conn, hug_conn, olap, watermark)
        log.info("hug_resolve: processed %d opt-in rows", n)
    finally:
        crm_conn.close()
        hug_conn.close()


def _hug_customer_push_run() -> None:
    """Push refreshed hug_customer rows to the Cloudflare Worker edge replica.

    Runs AFTER reverse_etl so wh_customer_tier is already fresh in cache.db.
    Config-gated: skips silently when HUG_WORKER_URL is unset (pre-deploy).
    """
    from hug.customer_push import run as push_run
    result = push_run()
    if result.get("skipped"):
        log.info("hug_customer_push: skipped — %s", result.get("reason", ""))
    elif result.get("error"):
        log.error("hug_customer_push: error — %s", result["error"])
    else:
        log.info(
            "hug_customer_push: %d/%d rows pushed, %d failed",
            result.get("ok", 0), result.get("total", 0), result.get("failed", 0),
        )


def _rebuild_search_index_run() -> None:
    """Rebuild crm_party_search FTS5 index from crm.db + cache.db."""
    import os as _os
    data_dir = _os.environ.get("CRM_DATA_DIR", "./data")
    import pathlib
    crm_db = str(pathlib.Path(data_dir) / "crm.db")
    cache_db = str(pathlib.Path(data_dir) / "cache.db")

    from crm.sync.search_index import rebuild_search_index
    n = rebuild_search_index(crm_db, cache_db)
    log.info("search_index: %d parties indexed", n)


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
            # Resolve new Hug opt-ins → crm_identity_link BEFORE the push, so a
            # customer just made contactable is reflected in the same refresh.
            # Best-effort: resolver failure must not abort the rest of the refresh.
            log.info("admin: hug_resolve starting")
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, _hug_resolve_run),
                    timeout=_REFRESH_TIMEOUT_S,
                )
            except Exception as resolve_exc:
                log.error("admin: hug_resolve failed (non-critical): %s", resolve_exc)
            # Push hug_customer replica to edge AFTER wh_customer_tier is fresh.
            # Best-effort: a push failure must not abort the rest of the refresh.
            log.info("admin: hug_customer_push starting")
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, _hug_customer_push_run),
                    timeout=_REFRESH_TIMEOUT_S,
                )
            except Exception as push_exc:
                log.error("admin: hug_customer_push failed (non-critical): %s", push_exc)
            log.info("admin: sync_parties starting")
            await asyncio.wait_for(
                loop.run_in_executor(None, _sync_parties_run),
                timeout=_REFRESH_TIMEOUT_S,
            )
            log.info("admin: rebuild_search_index starting")
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, _rebuild_search_index_run),
                    timeout=_REFRESH_TIMEOUT_S,
                )
            except Exception as idx_exc:
                log.error("admin: rebuild_search_index failed (non-critical): %s", idx_exc)
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
