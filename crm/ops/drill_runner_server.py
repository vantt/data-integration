"""Drill-runner sidecar: a tiny HTTP trigger for the CRM restore-verify drill.

Why this exists: the restore-verify drill MUST spin an ephemeral container, so
*something* behind the trigger needs the Docker socket. Rather than give the
orchestrator (`data_platform`, which runs dlt/dbt/Sapo code) socket access, this
single-purpose sidecar holds the socket, runs ONLY the drill, exposes NO public
route, and is token-gated. Smallest, most auditable blast radius for socket access.

`POST /run-drill` (header `X-Drill-Token`) runs `restore_verify_crm.py` in sidecar
mode (the runner has `crm_backups` + `crm_verify_data` mounted + the socket) and
returns `{status, exit_code, tail}`. A non-zero exit → HTTP 500 so the calling
Dagster asset reds + the failure sensor alerts. Runs are serialized (fixed
container name + single verify volume can't run concurrently).
"""

from __future__ import annotations

import asyncio
import os
import sys

from fastapi import FastAPI, Header, HTTPException

DRILL_TOKEN = os.environ.get("DRILL_TOKEN", "")
DRILL_SCRIPT = "/app/crm/ops/restore_verify_crm.py"
DRILL_TIMEOUT = int(os.environ.get("DRILL_TIMEOUT", "300"))  # boot+gate budget

app = FastAPI(title="crm-drill-runner")
_lock = asyncio.Lock()


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "token_configured": bool(DRILL_TOKEN)}


@app.post("/run-drill")
async def run_drill(
    x_drill_token: str = Header(default=""),
    negative: str | None = None,
) -> dict:
    if not DRILL_TOKEN or x_drill_token != DRILL_TOKEN:
        raise HTTPException(status_code=401, detail="bad or missing X-Drill-Token")
    if _lock.locked():
        raise HTTPException(status_code=409, detail="a drill is already running")

    async with _lock:
        cmd = [sys.executable, DRILL_SCRIPT]
        if negative:
            cmd += ["--negative", negative]
        env = {
            **os.environ,
            "CRM_VERIFY_DATA_DIR": "/verify_data",
            "CRM_BACKUPS_DIR": "/backups",
            "PYTHONUNBUFFERED": "1",
        }
        proc = await asyncio.create_subprocess_exec(
            *cmd, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=DRILL_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise HTTPException(status_code=504, detail=f"drill exceeded {DRILL_TIMEOUT}s")

        text = out.decode("utf-8", "replace")
        tail = "\n".join(text.splitlines()[-40:])
        body = {
            "status": "pass" if proc.returncode == 0 else "fail",
            "exit_code": proc.returncode,
            "tail": tail,
        }
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=body)
        return body
