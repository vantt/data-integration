"""Web adapter — M06 Custom Fields modal.

Routes:
  GET  /modals/m06?party_id=                open the custom-fields modal
  POST /customers/{party_id}/custom-fields  save custom field values
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.adapters.inbound.web.screen_modal_shared import (
    ProfileSvc,
    parse_custom,
    redirect_to_customer,
)

log = logging.getLogger(__name__)


def make_custom_fields_modal_router(templates: Jinja2Templates, profile: ProfileSvc) -> APIRouter:
    router = APIRouter()

    @router.get("/modals/m06", response_class=HTMLResponse)
    async def get_modal_m06(request: Request, party_id: str) -> Response:
        cf_defs = profile.list_custom_field_defs("party")
        p360 = profile.get_party_360(party_id)
        custom_vals = {k: str(v) for k, v in parse_custom(p360.custom if p360 else "").items()}
        return templates.TemplateResponse(
            "fragments/modal_m06_custom_fields.html",
            {"request": request, "party_id": party_id,
             "custom_field_defs": cf_defs, "custom_values": custom_vals},
        )

    @router.post("/customers/{party_id}/custom-fields", response_class=HTMLResponse)
    async def post_custom_fields(request: Request, party_id: str) -> Response:
        form_data = await request.form()
        cf_defs = profile.list_custom_field_defs("party")
        valid_keys = {d.field_key for d in cf_defs}
        try:
            p360 = profile.get_party_360(party_id)
            merged = parse_custom(p360.custom if p360 else "")
            for key in valid_keys:
                raw = form_data.get(key)
                if raw is not None:
                    merged[key] = str(raw).strip()
            profile.upsert_profile(party_id, custom=merged)
        except Exception as exc:
            log.error("post_custom_fields %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi lưu thông tin bổ sung: {exc}", status_code=500)
        return redirect_to_customer(party_id)

    return router
