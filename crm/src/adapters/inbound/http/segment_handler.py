"""Segment HTTP handlers — FastAPI APIRouter prefix=/api.

Auth: POST/PATCH/DELETE mutations require X-CRM-Token header (CRM_API_TOKEN env var).
GET endpoints are read-only and unauthenticated.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from adapters.inbound.http.auth_dependency import require_api_token

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SegmentCreateBody(BaseModel):
    name: str
    description: Optional[str] = None
    is_dynamic: bool = False
    definition: Optional[Any] = None
    owner_user_id: Optional[str] = None


class SegmentUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_dynamic: Optional[bool] = None
    definition: Optional[Any] = None
    owner_user_id: Optional[str] = None


class AddMemberBody(BaseModel):
    party_id: str


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def make_segment_router(
    segment_svc: Any,
) -> APIRouter:
    """Return an APIRouter wired to *segment_svc* (SegmentService instance).

    Keeps the handler thin: validation lives in the service layer.
    """
    router = APIRouter(prefix="/api")

    # ── GET /segments ────────────────────────────────────────────────────────

    @router.get("/segments")
    def list_segments():
        try:
            segs = segment_svc.list_segments()
        except Exception as exc:
            logger.exception("segment handler: list")
            raise HTTPException(status_code=500, detail="failed to list segments") from exc
        return {"segments": [asdict(s) for s in segs]}

    # ── POST /segments ───────────────────────────────────────────────────────

    @router.post("/segments", status_code=201, dependencies=[Depends(require_api_token)])
    def create_segment(body: SegmentCreateBody):
        try:
            seg = segment_svc.create_segment(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("segment handler: create")
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return asdict(seg)

    # ── PATCH /segments/{id} ─────────────────────────────────────────────────

    @router.patch("/segments/{segment_id}", dependencies=[Depends(require_api_token)])
    def update_segment(segment_id: str, body: SegmentUpdateBody):
        patch = {k: v for k, v in body.model_dump().items() if v is not None}
        try:
            segment_svc.update_segment(segment_id, **patch)
        except ValueError as exc:
            msg = str(exc)
            status = 404 if "not found" in msg else 400
            raise HTTPException(status_code=status, detail=msg) from exc
        except Exception as exc:
            logger.exception("segment handler: update %s", segment_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"status": "ok", "segment_id": segment_id}

    # ── POST /segments/{id}/refresh ──────────────────────────────────────────

    @router.post("/segments/{segment_id}/refresh", dependencies=[Depends(require_api_token)])
    def refresh_segment(segment_id: str):
        try:
            n = segment_svc.refresh_dynamic_segment(segment_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("segment handler: refresh %s", segment_id)
            raise HTTPException(status_code=500, detail="refresh failed") from exc
        return {"segment_id": segment_id, "members_refreshed": n}

    # ── GET /segments/{id}/members ───────────────────────────────────────────

    @router.get("/segments/{segment_id}/members")
    def list_members(segment_id: str):
        try:
            members = segment_svc.list_members(segment_id)
        except Exception as exc:
            logger.exception("segment handler: list members %s", segment_id)
            raise HTTPException(status_code=500, detail="failed to list members") from exc
        return {"members": [asdict(m) for m in members]}

    # ── POST /segments/{id}/members ──────────────────────────────────────────

    @router.post("/segments/{segment_id}/members", status_code=201, dependencies=[Depends(require_api_token)])
    def add_member(segment_id: str, body: AddMemberBody):
        try:
            segment_svc.add_member(segment_id, body.party_id)
        except Exception as exc:
            logger.exception("segment handler: add member %s→%s", segment_id, body.party_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"segment_id": segment_id, "party_id": body.party_id}

    # ── DELETE /segments/{id}/members/{party_id} ─────────────────────────────

    @router.delete("/segments/{segment_id}/members/{party_id}", dependencies=[Depends(require_api_token)])
    def remove_member(segment_id: str, party_id: str):
        try:
            segment_svc.remove_member(segment_id, party_id)
        except Exception as exc:
            logger.exception("segment handler: remove member %s→%s", segment_id, party_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"status": "removed"}

    return router
