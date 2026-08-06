"""Web adapter — Customer 360 Suggestion Settings panel (P07).

Extracted as its own module (not folded into screen_customer_360_panels.py) since it
owns 4 POST routes in addition to the panel render — mirrors screen_customer_360_tasks.py.
Registered by make_customer_360_router(); the returned render_panel callable is handed
to screen_customer_360_panels.py's dispatch chain (the {panel} catch-all route already
lives there — a competing literal route would be fragile against FastAPI's routing order).

do-not-contact here is a convenience SHORTCUT to the existing mechanism #3 (activity
outcome_reason='do_not_contact', WorklistQueryService) — it does not duplicate or
reimplement it. This module never touches crm_action_dismissal for that button.
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


class DoNotContactReader(Protocol):
    """Read side of mechanism #3 — same port WorklistQueryService depends on."""
    def list_do_not_contact_party_ids(self) -> set[str]: ...


class ActivityWriter(Protocol):
    """Write side of mechanism #3 — the same ActivityService the Call Cockpit
    'Đừng gọi nữa' pill and the full log-activity endpoint use."""
    def log_activity(self, activity_data: dict) -> object: ...


def register_suggestion_settings_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    settings_svc: Optional[SuggestionSettingsSvc] = None,
    dnc_reader: Optional[DoNotContactReader] = None,
    activity_log: Optional[ActivityWriter] = None,
):
    """Register the suppress/unsuppress/bulk-suppress/do-not-contact POST routes.

    Returns the render_panel coroutine — the caller (screen_customer_360.py) passes it
    into register_panel_routes() so the panel dispatch chain can call it for
    panel == "suggestion_settings".
    """

    def _uid(request: Request) -> Optional[str]:
        # No current_user (unauthenticated dev/test path) -> NULL owner, "Hệ thống" display —
        # matches list_active_dismissals' existing fallback. Never "" (FK requires NULL or
        # a real crm_app_user.user_id; "" is neither).
        return getattr(getattr(request.state, "current_user", None), "user_id", "") or None

    async def render_panel(request: Request, party_id: str) -> Response:
        if settings_svc is None:
            return HTMLResponse("suggestion settings service not available", status_code=503)
        groups = settings_svc.get_settings(party_id)
        is_do_not_contact = False
        if dnc_reader is not None:
            try:
                is_do_not_contact = party_id in dnc_reader.list_do_not_contact_party_ids()
            except Exception as exc:
                log.warning("c360 suggestion_settings: dnc check %s: %s", party_id, exc)
        return templates.TemplateResponse(
            "fragments/c360_suggestion_settings_panel.html",
            {"request": request, "party_id": party_id, "groups": groups,
             "is_do_not_contact": is_do_not_contact},
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
        try:
            settings_svc.suppress(party_id, action_type, source_mart, until_date, _uid(request))
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

    @router.post("/customers/{party_id}/suggestion-settings/bulk-suppress", response_class=HTMLResponse)
    async def handle_bulk_suppress(request: Request, party_id: str) -> Response:
        """Apply one end date to every checked (action_type|source_mart) row. Best-effort
        per row — one row failing validation (e.g. catalog drifted mid-session) must not
        block the rest; failures are logged, not surfaced individually (the panel re-render
        after is itself the feedback: a row that failed still shows "Đang bật")."""
        if settings_svc is None:
            return HTMLResponse("suggestion settings service not available", status_code=503)
        form = await request.form()
        row_keys = form.getlist("row_keys")
        until_date = str(form.get("until_date") or "").strip()
        if not row_keys:
            return HTMLResponse("Chưa chọn mục nào", status_code=400)
        if not until_date:
            return HTMLResponse("Vui lòng chọn ngày", status_code=400)
        uid = _uid(request)
        for row_key in row_keys:
            row_key = str(row_key)
            if "|" not in row_key:
                continue
            action_type, source_mart = row_key.split("|", 1)
            try:
                settings_svc.suppress(party_id, action_type, source_mart, until_date, uid)
            except Exception as exc:
                log.warning("c360 suggestion_settings: bulk suppress %s/%s: %s", party_id, row_key, exc)
        return await render_panel(request, party_id)

    @router.post("/customers/{party_id}/suggestion-settings/do-not-contact", response_class=HTMLResponse)
    async def handle_do_not_contact(request: Request, party_id: str) -> Response:
        """Shortcut to mechanism #3 — logs the same 'refused'/'do_not_contact' activity
        the Call Cockpit escalation pill writes. Does not touch crm_action_dismissal."""
        if activity_log is None:
            return HTMLResponse("activity service not available", status_code=503)
        try:
            activity_log.log_activity({
                "party_id": party_id,
                "activity_type": "call",
                "channel_type": "call",
                "contact_outcome": "refused",
                "outcome_reason": "do_not_contact",
                "staff_user_id": _uid(request),
            })
        except Exception as exc:
            log.error("c360 suggestion_settings: do_not_contact %s: %s", party_id, exc)
            return HTMLResponse("Không thể đặt trạng thái Đừng gọi nữa", status_code=400)
        return await render_panel(request, party_id)

    return render_panel
