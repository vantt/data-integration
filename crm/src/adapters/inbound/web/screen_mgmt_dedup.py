"""S04 Dedup review routes.

Candidate review list, merge-confirm modal, merge execution, and rejection.
Mirrors Go screen_dedup_review.go (same URL patterns, same redirect semantics).
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Form, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screen_mgmt_helpers import _build_dedup_party_names, _safe


def make_dedup_router(
    templates: Jinja2Templates,
    dedup_svc: Any,
    merger_svc: Any,
    parties_svc: Any,
) -> APIRouter:
    router = APIRouter()

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

    return router
