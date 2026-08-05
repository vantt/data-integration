"""Web adapter — Customer 360 Suggestion Settings panel (P07).

Extracted as its own module (not folded into screen_customer_360_panels.py) since it
owns 2 POST routes in addition to the panel render — mirrors screen_customer_360_tasks.py.
Registered by make_customer_360_router(); the returned render_panel callable is handed
to screen_customer_360_panels.py's dispatch chain (the {panel} catch-all route already
lives there — a competing literal route would be fragile against FastAPI's routing order).
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)


class SuggestionSettingsSvc(Protocol):
    """Narrow port the screen depends on — see application/suggestion_settings_service.py."""
    def get_settings(self, party_id: str) -> list: ...
    def suppress(self, party_id: str, action_type: str, source_mart: str,
                 until_date_ict: str, user_id: Optional[str] = None) -> None: ...
    def unsuppress(self, party_id: str, action_type: str, source_mart: str) -> None: ...


def register_suggestion_settings_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    settings_svc: Optional[SuggestionSettingsSvc] = None,
):
    """Register the suppress/unsuppress POST routes on *router*.

    Returns the render_panel coroutine — the caller (screen_customer_360.py) passes it
    into register_panel_routes() so the panel dispatch chain can call it for
    panel == "suggestion_settings".
    """

    async def render_panel(request: Request, party_id: str) -> Response:
        if settings_svc is None:
            return HTMLResponse("suggestion settings service not available", status_code=503)
        groups = settings_svc.get_settings(party_id)
        return templates.TemplateResponse(
            "fragments/c360_suggestion_settings_panel.html",
            {"request": request, "party_id": party_id, "groups": groups},
        )

    @router.post("/customers/{party_id}/suggestion-settings/suppress", response_class=HTMLResponse)
    async def handle_suppress(
        request: Request,
        party_id: str,
        action_type: str = Form(...),
        source_mart: str = Form(...),
        until_date: str = Form(...),
    ) -> Response:
        if settings_svc is None:
            return HTMLResponse("suggestion settings service not available", status_code=503)
        # No current_user (unauthenticated dev/test path) -> NULL owner, "Hệ thống" display —
        # matches list_active_dismissals' existing fallback. Never write "" (FK requires
        # NULL or a real crm_app_user.user_id; "" is neither).
        uid = getattr(getattr(request.state, "current_user", None), "user_id", "") or None
        try:
            settings_svc.suppress(party_id, action_type, source_mart, until_date, uid)
        except ValueError as exc:
            log.warning("c360 suggestion_settings: suppress %s/%s/%s: %s",
                        party_id, action_type, source_mart, exc)
            return HTMLResponse(str(exc), status_code=400)
        except Exception as exc:
            log.error("c360 suggestion_settings: suppress %s: %s", party_id, exc)
            return HTMLResponse("Không thể tắt gợi ý này — kiểm tra lại thông tin", status_code=400)
        return await render_panel(request, party_id)

    @router.post("/customers/{party_id}/suggestion-settings/unsuppress", response_class=HTMLResponse)
    async def handle_unsuppress(
        request: Request,
        party_id: str,
        action_type: str = Form(...),
        source_mart: str = Form(...),
    ) -> Response:
        if settings_svc is None:
            return HTMLResponse("suggestion settings service not available", status_code=503)
        try:
            settings_svc.unsuppress(party_id, action_type, source_mart)
        except Exception as exc:
            log.error("c360 suggestion_settings: unsuppress %s: %s", party_id, exc)
            return HTMLResponse("Không thể mở lại gợi ý này", status_code=400)
        return await render_panel(request, party_id)

    return render_panel
