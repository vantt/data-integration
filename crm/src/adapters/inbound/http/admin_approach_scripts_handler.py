"""admin_approach_scripts_handler.py — POST /admin/approach-scripts/load.

Receives already-lint-passed approach-script JSON from the auto-gen pipeline
(scripts/generate_approach_scripts.py --auto-load-url, phase 05) and writes
each into {scripts_dir}/{customer_id}.json. This container has no `scripts/`
mount (Dockerfile.crm only COPYs crm/) so it cannot re-run
approach_script_lint.py — trusts the caller already linted. Only validates
shape (customer_id: int, script: object) before an atomic write.

Auth mirrors /admin/refresh: X-Refresh-Token header == CRM_REFRESH_TOKEN env
(unset token = endpoint unprotected, LAN-trust only).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


def create_admin_approach_scripts_router(scripts_dir: str | Path) -> APIRouter:
    r = APIRouter()
    out_dir = Path(scripts_dir)

    @r.post("/admin/approach-scripts/load")
    async def post_approach_scripts_load(
        items: list[dict],
        x_refresh_token: str | None = Header(default=None),
    ) -> JSONResponse:
        token = os.environ.get("CRM_REFRESH_TOKEN", "")
        if token and x_refresh_token != token:
            raise HTTPException(status_code=401, detail={"status": "unauthorized"})
        if not token:
            log.warning(
                "admin: CRM_REFRESH_TOKEN unset — /admin/approach-scripts/load is UNPROTECTED (LAN-trust only)")

        out_dir.mkdir(parents=True, exist_ok=True)
        written = 0
        skipped: list[dict] = []
        for item in items:
            cid = item.get("customer_id")
            script = item.get("script")
            if not isinstance(cid, int) or not isinstance(script, dict):
                skipped.append({"customer_id": cid, "reason": "missing/invalid customer_id or script"})
                continue
            target = out_dir / f"{cid}.json"
            tmp = out_dir / f".{cid}.json.tmp"
            try:
                tmp.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
                os.replace(tmp, target)
                written += 1
            except OSError as exc:
                log.error("approach-scripts/load: write failed cid=%s: %s", cid, exc)
                skipped.append({"customer_id": cid, "reason": f"write failed: {exc}"})

        log.info("admin: approach-scripts/load written=%d skipped=%d", written, len(skipped))
        return JSONResponse(status_code=200, content={"written": written, "skipped": skipped})

    return r
