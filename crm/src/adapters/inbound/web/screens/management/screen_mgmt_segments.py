"""S08 Segments management routes.

Segment list, builder (create/edit), dynamic refresh, and member add/remove.
Mirrors Go screen_segments.go (same URL patterns, same redirect semantics).
"""
from __future__ import annotations

from typing import Any, Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.management.screen_mgmt_helpers import _build_rule_definition, _safe
from domain.entities.segment import Segment, SegmentMember


class SegmentsSvc(Protocol):
    """Structural protocol for the segments service used by make_segments_router."""

    def list_segments(self) -> list[Segment]: ...
    def count_members_for_segments(self, segment_ids: list[str]) -> dict[str, int]: ...
    def create_segment(self, data: dict) -> Segment: ...
    def get_segment(self, segment_id: str) -> Optional[Segment]: ...
    def list_members(self, segment_id: str) -> list[SegmentMember]: ...
    def update_segment(self, segment_id: str, **kwargs: Any) -> None: ...
    def refresh_dynamic_segment(self, segment_id: str) -> int: ...
    def add_member(self, segment_id: str, party_id: str) -> None: ...
    def remove_member(self, segment_id: str, party_id: str) -> None: ...


def make_segments_router(
    templates: Jinja2Templates,
    segments_svc: SegmentsSvc,
) -> APIRouter:
    router = APIRouter()

    @router.get("/segments", response_class=HTMLResponse)
    def segments_list(request: Request):
        segs = _safe(segments_svc.list_segments, [], "segments list")
        # Batch count in one query instead of N per-segment queries.
        seg_ids = [s.segment_id for s in segs]
        counts = _safe(
            lambda: segments_svc.count_members_for_segments(seg_ids),
            {sid: 0 for sid in seg_ids},
            "segment member counts",
        )
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
        seg = segments_svc.create_segment({
            "name": name.strip(),
            "description": description.strip(),
            "is_dynamic": (is_dynamic == "true"),
            "definition": definition,
        })
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

    return router
