"""Web adapter — M04 Assign Owner modal.

Routes:
  GET /modals/m04?party_id=   open the assign-owner modal
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.modals.screen_modal_shared import AppUserRepo, ProfileSvc

log = logging.getLogger(__name__)


def make_owner_modal_router(
    templates: Jinja2Templates,
    profile: ProfileSvc,
    app_users: AppUserRepo,
) -> APIRouter:
    router = APIRouter()

    @router.get("/modals/m04", response_class=HTMLResponse)
    async def get_modal_m04(request: Request, party_id: str) -> Response:
        current_owner_id: Optional[str] = None
        p360 = profile.get_party_360(party_id)
        if p360:
            current_owner_id = p360.owner_user_id
        users = []
        try:
            users = app_users.list_active()
        except Exception as exc:
            log.warning("m04: list_active: %s", exc)
        current_owner_name = next(
            (u.full_name for u in users if u.user_id == current_owner_id), current_owner_id
        )
        return templates.TemplateResponse(
            "modals.html",
            {"request": request, "macro": "modal_assign_owner",
             "party_id": party_id, "current_owner_id": current_owner_id,
             "current_owner_name": current_owner_name, "users": users},
        )

    return router
