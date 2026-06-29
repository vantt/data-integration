"""S10 Campaigns management routes.

Campaign list/detail, create/edit modals, target generation, conversion
scanning, and per-target status updates. Mirrors Go screen_campaigns.go
(same URL patterns, same redirect semantics).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.management.screen_mgmt_helpers import _build_party_names, _safe


def make_campaigns_router(
    templates: Jinja2Templates,
    campaigns_svc: Any,
    segments_svc: Any,
    parties_svc: Any,
    app_users_svc: Any,
) -> APIRouter:
    router = APIRouter()

    @router.get("/campaigns", response_class=HTMLResponse)
    def campaigns_list(request: Request):
        cps = _safe(campaigns_svc.list_campaigns, [], "campaigns list")
        seg_names: dict[str, str] = {}
        for c in cps:
            if c.segment_id and c.segment_id not in seg_names:
                s = _safe(lambda sid=c.segment_id: segments_svc.get_segment(sid), None, "")
                if s:
                    seg_names[c.segment_id] = s.name
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaigns": cps, "segment_names": seg_names,
            "view": "list",
        })

    @router.get("/campaigns/modal/create", response_class=HTMLResponse)
    def modal_create_campaign(request: Request):
        segs = _safe(segments_svc.list_segments, [], "modal create: segments")
        users = _safe(app_users_svc.list_active, [], "modal create: users")
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "segments": segs, "users": users,
            "view": "modal_create",
        })

    @router.post("/campaigns")
    async def campaign_create(
        name: str = Form(""), objective: str = Form(""),
        channel: str = Form(""), segment_id: str = Form(""),
        scheduled_at: str = Form(""),
    ):
        sid = segment_id.strip() or None
        if scheduled_at.strip():
            from datetime import datetime, timezone, timedelta
            _ICT = timezone(timedelta(hours=7))
            ts = (
                datetime.strptime(scheduled_at.strip(), "%Y-%m-%d")
                .replace(tzinfo=_ICT)
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S.000Z")
            )
        else:
            ts = None
        c = campaigns_svc.create_campaign({
            "name": name.strip(),
            "objective": objective.strip(),
            "channel": channel.strip(),
            "segment_id": sid,
            "scheduled_at": ts,
            "status": "draft",
        })
        return Response(status_code=200, headers={"HX-Redirect": f"/campaigns/{c.campaign_id}"})

    @router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
    def campaign_detail(request: Request, campaign_id: str):
        c = campaigns_svc.get_campaign(campaign_id)
        if not c:
            return HTMLResponse("Chiến dịch không tìm thấy", status_code=404)
        targets = _safe(lambda: campaigns_svc.list_targets(campaign_id, ""), [], "targets")
        roi = _safe(lambda: campaigns_svc.get_roi(campaign_id), None, "roi")
        party_names = _build_party_names(parties_svc, targets)
        seg_name = ""
        if c.segment_id:
            s = _safe(lambda: segments_svc.get_segment(c.segment_id), None, "")
            if s:
                seg_name = s.name
        user_map = {u.user_id: u.full_name for u in _safe(app_users_svc.list_active, [], "user_map")}
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign": c, "targets": targets,
            "roi": roi, "party_names": party_names, "segment_name": seg_name,
            "user_map": user_map, "view": "detail",
        })

    @router.get("/campaigns/{campaign_id}/modal/edit", response_class=HTMLResponse)
    def modal_edit_campaign(request: Request, campaign_id: str):
        c = campaigns_svc.get_campaign(campaign_id)
        if not c:
            return HTMLResponse("not found", status_code=404)
        segs = _safe(segments_svc.list_segments, [], "")
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign": c, "segments": segs,
            "view": "modal_edit",
        })

    @router.patch("/campaigns/{campaign_id}")
    async def campaign_update(
        campaign_id: str,
        name: str = Form(""), objective: str = Form(""),
        channel: str = Form(""), segment_id: str = Form(""),
    ):
        sid = segment_id.strip() or None
        campaigns_svc.update_campaign(
            campaign_id, name=name.strip(),
            objective=objective.strip(), channel=channel.strip(),
            segment_id=sid,
        )
        return Response(status_code=200, headers={"HX-Redirect": f"/campaigns/{campaign_id}"})

    @router.post("/campaigns/{campaign_id}/generate-targets", response_class=HTMLResponse)
    def generate_targets(request: Request, campaign_id: str):
        _safe(lambda: campaigns_svc.generate_targets(campaign_id), 0, "gen targets")
        targets = _safe(lambda: campaigns_svc.list_targets(campaign_id, ""), [], "")
        party_names = _build_party_names(parties_svc, targets)
        user_map = {u.user_id: u.full_name for u in _safe(app_users_svc.list_active, [], "user_map")}
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign_id": campaign_id,
            "targets": targets, "party_names": party_names,
            "user_map": user_map, "view": "target_list",
        })

    @router.post("/campaigns/{campaign_id}/scan-conversions", response_class=HTMLResponse)
    def scan_conversions(request: Request, campaign_id: str):
        _safe(lambda: campaigns_svc.scan_conversions(campaign_id), 0, "scan conv")
        roi = _safe(lambda: campaigns_svc.get_roi(campaign_id), None, "roi")
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "roi": roi, "view": "roi_fragment",
        })

    @router.get("/campaigns/{campaign_id}/targets/{party_id}/modal/convert",
                response_class=HTMLResponse)
    def modal_convert(request: Request, campaign_id: str, party_id: str):
        p = _safe(lambda: parties_svc.get_by_id(party_id), None, "")
        party_name = p.display_name if p else party_id
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign_id": campaign_id,
            "party_id": party_id, "party_name": party_name,
            "view": "modal_convert",
        })

    @router.post("/campaigns/{campaign_id}/targets/{party_id}/convert")
    async def record_conversion(
        campaign_id: str, party_id: str,
        order_code: str = Form(""), revenue_vnd: str = Form(""),
    ):
        rev = None
        if revenue_vnd.strip():
            try:
                rev = int(revenue_vnd.strip())
            except ValueError:
                pass
        campaigns_svc.record_conversion(
            campaign_id, party_id,
            order_code=order_code.strip() or None,
            revenue_vnd=rev,
        )
        headers = {"HX-Trigger": '{"closeModal":true}',
                   "HX-Redirect": f"/campaigns/{campaign_id}"}
        return Response(status_code=200, headers=headers)

    @router.patch("/campaigns/{campaign_id}/targets/{party_id}/status",
                  response_class=HTMLResponse)
    async def update_target_status(
        request: Request, campaign_id: str, party_id: str,
        status: str = Form(""),
    ):
        campaigns_svc.update_target_status(campaign_id, party_id, status.strip())
        t = campaigns_svc.get_target(campaign_id, party_id)
        if not t:
            return HTMLResponse("target not found", status_code=404)
        p = _safe(lambda: parties_svc.get_by_id(party_id), None, "")
        party_names = {party_id: p.display_name} if p else {}
        user_map = {u.user_id: u.full_name for u in _safe(app_users_svc.list_active, [], "user_map")}
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign_id": campaign_id,
            "target": t, "party_names": party_names,
            "user_map": user_map, "view": "target_row",
        })

    return router
