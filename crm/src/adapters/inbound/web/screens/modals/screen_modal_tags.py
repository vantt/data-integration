"""Web adapter — M03 Tag Management modal.

Routes:
  GET  /modals/m03?party_id=        open the tag-management modal
  POST /customers/{party_id}/tags   save tag selection (attach/detach diff)
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.modals.screen_modal_shared import ProfileSvc, redirect_to_customer

log = logging.getLogger(__name__)


def make_tags_modal_router(templates: Jinja2Templates, profile: ProfileSvc) -> APIRouter:
    router = APIRouter()

    @router.get("/modals/m03", response_class=HTMLResponse)
    async def get_modal_m03(request: Request, party_id: str) -> Response:
        all_tags = profile.list_tags("")
        current = profile.list_party_tags(party_id)
        party_tag_ids = {t.tag_id for t in current}
        party_name = ""
        try:
            p360 = profile.get_party_360(party_id)
            if p360:
                party_name = p360.display_name
        except Exception:
            pass
        return templates.TemplateResponse(
            "fragments/modal_m03_tags.html",
            {"request": request, "party_id": party_id,
             "all_tags": all_tags, "party_tag_ids": party_tag_ids,
             "party_name": party_name},
        )

    @router.post("/customers/{party_id}/tags", response_class=HTMLResponse)
    async def post_tags(
        party_id: str,
        tag_ids: List[str] = Form(default=[]),
    ) -> Response:
        current = profile.list_party_tags(party_id)
        current_ids = {t.tag_id for t in current}
        submitted = set(tag_ids)
        try:
            for tid in current_ids - submitted:
                profile.detach_tag(party_id, tid)
            for tid in submitted - current_ids:
                profile.attach_tag(party_id, tid)
        except Exception as exc:
            log.error("post_tags %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu tags: {exc}", status_code=500)
        return redirect_to_customer(party_id)

    return router
