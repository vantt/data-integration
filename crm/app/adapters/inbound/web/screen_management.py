"""Management screen handlers — segments, campaigns, dedup, settings.

FastAPI router mounting all four management screens and their HTMX fragments.
Mirrors Go screen_segments.go / screen_campaigns.go / screen_dedup_review.go /
screen_settings.go exactly (same URL patterns, same redirect semantics).
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _is_valid_hex_color(color: str) -> bool:
    return color == "" or bool(_HEX_RE.match(color))


def _build_rule_definition(
    value_group: list[str],
    customer_status: str,
    days_since: str,
    channel: str,
) -> str:
    rule: dict[str, Any] = {}
    if value_group:
        rule["value_group"] = value_group
    if customer_status.strip():
        rule["customer_status"] = customer_status.strip()
    if days_since.strip():
        try:
            n = int(days_since.strip())
            if n > 0:
                rule["days_since_last_order_gte"] = n
        except ValueError:
            pass
    if channel.strip():
        rule["channel_preference"] = channel.strip()
    return json.dumps(rule) if rule else ""


def _parse_options(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


# ---------------------------------------------------------------------------

def make_management_router(
    templates: Jinja2Templates,
    segments_svc: Any,
    campaigns_svc: Any,
    dedup_svc: Any,
    merger_svc: Any,
    parties_svc: Any,
    settings_svc: Any,
    app_users_svc: Any,
) -> APIRouter:
    router = APIRouter()

    # ── S08 Segments list ────────────────────────────────────────────────────

    @router.get("/segments", response_class=HTMLResponse)
    def segments_list(request: Request):
        segs = _safe(segments_svc.list_segments, [], "segments list")
        counts = {}
        for s in segs:
            members = _safe(lambda: segments_svc.list_members(s.segment_id), [], "")
            counts[s.segment_id] = len(members)
        return templates.TemplateResponse("segments.html", {
            "request": request, "segments": segs, "member_counts": counts,
        })

    @router.get("/segments/new", response_class=HTMLResponse)
    def segment_new(request: Request):
        return templates.TemplateResponse("segments.html", {
            "request": request, "segment": None, "members": [], "is_new": True,
            "view": "builder",
        })

    @router.post("/segments")
    async def segment_create(
        request: Request,
        name: str = Form(""),
        description: str = Form(""),
        is_dynamic: str = Form("false"),
        rule_value_group: list[str] = Form(default=[]),
        rule_customer_status: str = Form(""),
        rule_days_since: str = Form(""),
        rule_channel: str = Form(""),
    ):
        definition = _build_rule_definition(
            rule_value_group, rule_customer_status, rule_days_since, rule_channel
        )
        seg = segments_svc.create_segment(
            name=name.strip(),
            description=description.strip(),
            is_dynamic=(is_dynamic == "true"),
            definition=definition,
        )
        return Response(status_code=200, headers={"HX-Redirect": f"/segments/{seg.segment_id}"})

    @router.get("/segments/{segment_id}", response_class=HTMLResponse)
    def segment_edit(request: Request, segment_id: str):
        seg = segments_svc.get_segment(segment_id)
        if not seg:
            return HTMLResponse("Segment không tìm thấy", status_code=404)
        members = _safe(lambda: segments_svc.list_members(segment_id), [], "segment members")
        return templates.TemplateResponse("segments.html", {
            "request": request, "segment": seg, "members": members,
            "is_new": False, "view": "builder",
        })

    @router.put("/segments/{segment_id}")
    async def segment_update(
        segment_id: str,
        name: str = Form(""),
        description: str = Form(""),
        is_dynamic: str = Form("false"),
        rule_value_group: list[str] = Form(default=[]),
        rule_customer_status: str = Form(""),
        rule_days_since: str = Form(""),
        rule_channel: str = Form(""),
    ):
        definition = _build_rule_definition(
            rule_value_group, rule_customer_status, rule_days_since, rule_channel
        )
        segments_svc.update_segment(
            segment_id=segment_id, name=name.strip(),
            description=description.strip(),
            is_dynamic=(is_dynamic == "true"), definition=definition,
        )
        return Response(status_code=200, headers={"HX-Redirect": f"/segments/{segment_id}"})

    @router.post("/segments/{segment_id}/refresh", response_class=HTMLResponse)
    def segment_refresh(request: Request, segment_id: str):
        count = _safe(lambda: segments_svc.refresh_dynamic_segment(segment_id), 0, "refresh")
        seg = segments_svc.get_segment(segment_id)
        if not seg:
            return HTMLResponse("segment not found", status_code=404)
        return templates.TemplateResponse("segments.html", {
            "request": request, "segment": seg, "member_count": count,
            "view": "row_refreshed",
        })

    @router.post("/segments/{segment_id}/members")
    async def segment_add_member(
        segment_id: str, party_id: str = Form("")
    ):
        if not party_id.strip():
            return HTMLResponse("party_id required", status_code=400)
        segments_svc.add_member(segment_id, party_id.strip())
        return Response(status_code=200, headers={"HX-Redirect": f"/segments/{segment_id}"})

    @router.delete("/segments/{segment_id}/members/{party_id}")
    def segment_remove_member(segment_id: str, party_id: str):
        segments_svc.remove_member(segment_id, party_id)
        return Response(status_code=200, headers={"HX-Redirect": f"/segments/{segment_id}"})

    # ── S10 Campaigns list ───────────────────────────────────────────────────

    @router.get("/campaigns", response_class=HTMLResponse)
    def campaigns_list(request: Request):
        cps = _safe(campaigns_svc.list_campaigns, [], "campaigns list")
        seg_names: dict[str, str] = {}
        for c in cps:
            if c.segment_id and c.segment_id not in seg_names:
                s = _safe(lambda: segments_svc.get_segment(c.segment_id), None, "")
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
        ts = (scheduled_at.strip() + "T00:00:00+07:00") if scheduled_at.strip() else None
        c = campaigns_svc.create_campaign(
            name=name.strip(), objective=objective.strip(),
            channel=channel.strip(), segment_id=sid,
            scheduled_at=ts, status="draft",
        )
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
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign": c, "targets": targets,
            "roi": roi, "party_names": party_names, "segment_name": seg_name,
            "view": "detail",
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
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign_id": campaign_id,
            "targets": targets, "party_names": party_names,
            "view": "target_list",
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
        return templates.TemplateResponse("campaigns.html", {
            "request": request, "campaign_id": campaign_id,
            "target": t, "party_names": party_names,
            "view": "target_row",
        })

    # ── S04 Dedup review ─────────────────────────────────────────────────────

    @router.get("/dedup", response_class=HTMLResponse)
    def dedup_review(request: Request, match_rule: str = Query(default="")):
        candidates = _safe(lambda: dedup_svc.list_candidates("pending"), [], "dedup list")
        if match_rule:
            candidates = [c for c in candidates if c.match_rule == match_rule]
        party_names = _build_dedup_party_names(parties_svc, candidates)
        return templates.TemplateResponse("dedup_review.html", {
            "request": request, "candidates": candidates,
            "party_names": party_names, "match_rule_filter": match_rule,
        })

    @router.get("/dedup/{candidate_id}/modal/merge", response_class=HTMLResponse)
    def modal_merge_confirm(request: Request, candidate_id: str):
        cand = dedup_svc.get_candidate(candidate_id)
        if not cand:
            return HTMLResponse("Không tìm thấy candidate", status_code=404)
        party_a = _safe(lambda: parties_svc.get_by_id(cand.party_a), None, "")
        party_b = _safe(lambda: parties_svc.get_by_id(cand.party_b), None, "")
        return templates.TemplateResponse("dedup_review.html", {
            "request": request, "candidate": cand,
            "party_a": party_a, "party_b": party_b,
            "view": "modal_merge",
        })

    @router.post("/dedup/{candidate_id}/merge")
    async def merge_parties(candidate_id: str, confirm: str = Form("0")):
        if confirm != "1":
            return HTMLResponse("xác nhận bắt buộc", status_code=400)
        cand = dedup_svc.get_candidate(candidate_id)
        if not cand:
            return HTMLResponse("candidate not found", status_code=404)
        merger_svc.merge(cand.party_a, cand.party_b, "manual dedup review")
        dedup_svc.update_candidate_status(candidate_id, "merged")
        headers = {"HX-Trigger": '{"closeModal":true}', "HX-Redirect": "/dedup"}
        return Response(status_code=200, headers=headers)

    @router.post("/dedup/{candidate_id}/reject")
    def reject_candidate(candidate_id: str):
        dedup_svc.update_candidate_status(candidate_id, "rejected")
        payload = json.dumps({"candidateRejected": candidate_id})
        return Response(status_code=200, headers={"HX-Trigger": payload})

    # ── S13 Settings ─────────────────────────────────────────────────────────

    @router.get("/settings", response_class=HTMLResponse)
    def settings(request: Request, tab: str = Query(default="custom_fields")):
        fields = _safe(lambda: settings_svc.list_custom_field_defs("party"), [], "cfd")
        tags = _safe(lambda: settings_svc.list_tags(""), [], "tags")
        users = _safe(app_users_svc.list_active, [], "users")
        return templates.TemplateResponse("settings.html", {
            "request": request, "active_tab": tab,
            "custom_fields": fields, "tags": tags, "users": users,
        })

    @router.get("/settings/custom-fields/modal/create", response_class=HTMLResponse)
    def modal_custom_field_create(request: Request):
        return templates.TemplateResponse("settings.html", {
            "request": request, "field": None, "is_new": True, "view": "modal_cfd",
        })

    @router.post("/settings/custom-fields")
    async def custom_field_create(
        field_key: str = Form(""), label: str = Form(""),
        data_type: str = Form(""), is_required: str = Form("false"),
        options: str = Form(""),
    ):
        if not field_key.strip() or not label.strip():
            return HTMLResponse("field_key and label required", status_code=400)
        settings_svc.create_custom_field_def(
            field_id=str(uuid.uuid4()), entity_type="party",
            field_key=field_key.strip(), label=label.strip(),
            data_type=data_type.strip(), is_required=(is_required == "true"),
            is_active=True, options=_parse_options(options),
        )
        return Response(status_code=200,
                        headers={"HX-Redirect": "/settings?tab=custom_fields"})

    @router.get("/settings/custom-fields/{field_id}/modal/edit",
                response_class=HTMLResponse)
    def modal_custom_field_edit(request: Request, field_id: str):
        f = settings_svc.get_custom_field_def(field_id)
        if not f:
            return HTMLResponse("field not found", status_code=404)
        return templates.TemplateResponse("settings.html", {
            "request": request, "field": f, "is_new": False, "view": "modal_cfd",
        })

    @router.patch("/settings/custom-fields/{field_id}")
    async def custom_field_update(
        field_id: str,
        label: str = Form(""), data_type: str = Form(""),
        is_required: str = Form("false"), options: str = Form(""),
    ):
        settings_svc.update_custom_field_def(
            field_id=field_id, label=label.strip(),
            data_type=data_type.strip(), is_required=(is_required == "true"),
            is_active=True, options=_parse_options(options),
        )
        return Response(status_code=200,
                        headers={"HX-Redirect": "/settings?tab=custom_fields"})

    @router.get("/settings/tags/modal/create", response_class=HTMLResponse)
    def modal_tag_create(request: Request):
        return templates.TemplateResponse("settings.html", {
            "request": request, "view": "modal_tag",
        })

    @router.post("/settings/tags")
    async def tag_create(
        name: str = Form(""), color: str = Form(""),
        category: str = Form(""),
    ):
        if not name.strip():
            return HTMLResponse("name required", status_code=400)
        if not _is_valid_hex_color(color.strip()):
            return HTMLResponse("invalid color: must be #RRGGBB or empty", status_code=400)
        settings_svc.create_tag(
            tag_id=str(uuid.uuid4()), name=name.strip(),
            category=category.strip(), color=color.strip(),
        )
        return Response(status_code=200, headers={"HX-Redirect": "/settings?tab=tags"})

    return router


# ---------------------------------------------------------------------------
# helpers

def _safe(fn, default, label: str):
    try:
        return fn()
    except Exception:
        if label:
            logger.exception("%s", label)
        return default


def _build_party_names(parties_svc: Any, targets: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for t in targets:
        if t.party_id in out:
            continue
        p = _safe(lambda: parties_svc.get_by_id(t.party_id), None, "")
        if p:
            out[t.party_id] = p.display_name
    return out


def _build_dedup_party_names(parties_svc: Any, candidates: list) -> dict[str, str]:
    seen: set[str] = set()
    out: dict[str, str] = {}
    for c in candidates:
        for pid in (c.party_a, c.party_b):
            if pid in seen:
                continue
            seen.add(pid)
            p = _safe(lambda: parties_svc.get_by_id(pid), None, "")
            if p:
                out[pid] = p.display_name
    return out
