"""HTTP adapter — Activity endpoints.

Auth: DEFERRED — LAN-trust only.
"""
from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from application.activity_service import ActivityService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── request schema ────────────────────────────────────────────────────────────

class LogActivityRequest(BaseModel):
    activity_type: str
    occurred_at: str = ""
    direction: str | None = None
    channel: str | None = None
    subject: str | None = None
    body: str | None = None
    outcome: str | None = None
    related_order_code: str | None = None
    staff_user_id: str | None = None


# ── dependency holder (set at app startup via wire_activity_router) ────────────

_svc: ActivityService | None = None


def wire_activity_router(svc: ActivityService) -> None:
    """Bind the application service; called during app startup."""
    global _svc
    _svc = svc


def _service() -> ActivityService:
    if _svc is None:
        raise RuntimeError("ActivityService not wired")
    return _svc


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/parties/{party_id}/activities", status_code=201)
def log_activity(party_id: str, req: LogActivityRequest):
    """POST /api/parties/{id}/activities — log a touchpoint for a party."""
    data = req.model_dump()
    data["party_id"] = party_id
    try:
        activity = _service().log_activity(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("activity handler: log_activity party=%s: %s", party_id, exc)
        raise HTTPException(status_code=500, detail="operation failed")
    return JSONResponse(status_code=201, content=dataclasses.asdict(activity))


@router.get("/parties/{party_id}/activities")
def list_timeline(party_id: str, limit: int = 50):
    """GET /api/parties/{id}/activities — timeline newest-first."""
    try:
        acts = _service().list_activities(party_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("activity handler: list_timeline party=%s: %s", party_id, exc)
        raise HTTPException(status_code=500, detail="failed to list activities")
    return {"party_id": party_id, "activities": [dataclasses.asdict(a) for a in acts]}
