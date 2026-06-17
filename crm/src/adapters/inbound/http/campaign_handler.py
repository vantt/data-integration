"""Campaign HTTP handlers — FastAPI APIRouter prefix=/api.

Auth: DEFERRED — LAN-trust only (per plan).
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CampaignCreateBody(BaseModel):
    name: str
    objective: str
    channel: str
    segment_id: Optional[str] = None
    scheduled_at: Optional[str] = None
    created_by: Optional[str] = None


class CampaignUpdateBody(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    channel: Optional[str] = None
    segment_id: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None


class TargetUpdateBody(BaseModel):
    status: Optional[str] = None
    assigned_user_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def make_campaign_router(campaign_svc: Any) -> APIRouter:
    """Return an APIRouter wired to *campaign_svc* (CampaignService instance).

    Keeps the handler thin: validation and business rules live in the service layer.
    """
    router = APIRouter(prefix="/api")

    # ── GET /campaigns ───────────────────────────────────────────────────────

    @router.get("/campaigns")
    def list_campaigns():
        try:
            campaigns = campaign_svc.list_campaigns()
        except Exception as exc:
            logger.exception("campaign handler: list")
            raise HTTPException(status_code=500, detail="failed to list campaigns") from exc
        return {"campaigns": [asdict(c) for c in campaigns]}

    # ── POST /campaigns ──────────────────────────────────────────────────────

    @router.post("/campaigns", status_code=201)
    def create_campaign(body: CampaignCreateBody):
        try:
            campaign = campaign_svc.create_campaign(body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("campaign handler: create")
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return asdict(campaign)

    # ── PATCH /campaigns/{id} ────────────────────────────────────────────────

    @router.patch("/campaigns/{campaign_id}")
    def update_campaign(campaign_id: str, body: CampaignUpdateBody):
        patch = {k: v for k, v in body.model_dump().items() if v is not None}
        try:
            campaign_svc.update_campaign(campaign_id, **patch)
        except ValueError as exc:
            msg = str(exc)
            status = 404 if "not found" in msg else 400
            raise HTTPException(status_code=status, detail=msg) from exc
        except Exception as exc:
            logger.exception("campaign handler: update %s", campaign_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"status": "ok", "campaign_id": campaign_id}

    # ── POST /campaigns/{id}/generate-targets ────────────────────────────────

    @router.post("/campaigns/{campaign_id}/generate-targets")
    def generate_targets(campaign_id: str):
        try:
            n = campaign_svc.generate_targets(campaign_id)
        except ValueError as exc:
            msg = str(exc)
            status = 404 if "not found" in msg else 400
            raise HTTPException(status_code=status, detail=msg) from exc
        except Exception as exc:
            logger.exception("campaign handler: generate targets %s", campaign_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"campaign_id": campaign_id, "targets_created": n}

    # ── GET /campaigns/{id}/targets ──────────────────────────────────────────

    @router.get("/campaigns/{campaign_id}/targets")
    def list_targets(campaign_id: str, status: Optional[str] = Query(default=None)):
        try:
            targets = campaign_svc.list_targets(campaign_id, status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("campaign handler: list targets %s", campaign_id)
            raise HTTPException(status_code=500, detail="failed to list targets") from exc
        return {"targets": [asdict(t) for t in targets]}

    # ── PATCH /campaigns/{id}/targets/{party_id} ─────────────────────────────
    # body: {"status": "sent"} or {"assigned_user_id": "..."} or both

    @router.patch("/campaigns/{campaign_id}/targets/{party_id}")
    def update_target(campaign_id: str, party_id: str, body: TargetUpdateBody):
        patch = {k: v for k, v in body.model_dump().items() if v is not None}
        if not patch:
            raise HTTPException(status_code=400, detail="no fields to update")
        try:
            campaign_svc.update_target(campaign_id, party_id, **patch)
        except ValueError as exc:
            msg = str(exc)
            status_code = 404 if "not found" in msg else 400
            raise HTTPException(status_code=status_code, detail=msg) from exc
        except Exception as exc:
            logger.exception(
                "campaign handler: update target (%s, %s)", campaign_id, party_id
            )
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"status": "ok"}

    # ── POST /campaigns/{id}/scan-conversions ────────────────────────────────

    @router.post("/campaigns/{campaign_id}/scan-conversions")
    def scan_conversions(campaign_id: str):
        try:
            n = campaign_svc.scan_conversions(campaign_id)
        except ValueError as exc:
            msg = str(exc)
            status = 404 if "not found" in msg else 400
            raise HTTPException(status_code=status, detail=msg) from exc
        except Exception as exc:
            logger.exception("campaign handler: scan conversions %s", campaign_id)
            raise HTTPException(status_code=500, detail="operation failed") from exc
        return {"campaign_id": campaign_id, "newly_converted": n}

    # ── GET /campaigns/{id}/roi ──────────────────────────────────────────────

    @router.get("/campaigns/{campaign_id}/roi")
    def get_roi(campaign_id: str):
        try:
            roi = campaign_svc.get_roi(campaign_id)
        except Exception as exc:
            logger.exception("campaign handler: roi %s", campaign_id)
            raise HTTPException(status_code=500, detail="failed to compute ROI") from exc
        return roi

    return router
