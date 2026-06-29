"""HTTP adapter — Activity endpoints.

Auth: POST mutation requires X-CRM-Token header (CRM_API_TOKEN env var).
GET endpoints are read-only and unauthenticated.
"""
from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from adapters.inbound.http.auth_dependency import require_api_token
from application.activity_service import ActivityService

log = logging.getLogger(__name__)


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


def make_activity_router(svc: ActivityService) -> APIRouter:
    """Factory — returns a router with the application service closed over."""
    router = APIRouter(prefix="/api")

    @router.post("/parties/{party_id}/activities", status_code=201, dependencies=[Depends(require_api_token)])
    def log_activity(party_id: str, req: LogActivityRequest):
        """POST /api/parties/{id}/activities — log a touchpoint for a party."""
        data = req.model_dump()
        data["party_id"] = party_id
        try:
            activity = svc.log_activity(data)
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
            acts = svc.list_activities(party_id, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            log.error("activity handler: list_timeline party=%s: %s", party_id, exc)
            raise HTTPException(status_code=500, detail="failed to list activities")
        return {"party_id": party_id, "activities": [dataclasses.asdict(a) for a in acts]}

    return router
