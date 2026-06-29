"""Web adapter — Customer 360 task quick-action (PATCH) and O03 modal routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_task_routes().
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)

_ICT = timezone(timedelta(hours=7))


def _ict_local_to_utc(ict_str: str) -> str:
    """Parse datetime-local input (assumed ICT/UTC+7) → UTC ISO-8601 string."""
    try:
        dt = datetime.strptime(ict_str.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=_ICT)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ""


def register_task_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    party_tasks,
    task_svc=None,
    app_users=None,
) -> None:
    """Register task quick-action (PATCH x3) and O03 postpone-modal (GET) routes on *router*."""

    def _render_tasks_panel(request: Request, party_id: str, filter_val: str = "open") -> Response:
        task_list = party_tasks.list_by_party(party_id)
        user_map: dict = {}
        if app_users is not None:
            try:
                user_map = {u.user_id: u.full_name for u in app_users.list_active()}
            except Exception:
                pass
        return templates.TemplateResponse(
            "fragments/c360_tasks_panel.html",
            {
                "request": request,
                "party_id": party_id,
                "tasks": task_list,
                "filter": filter_val,
                "user_map": user_map,
                "now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        )

    @router.patch("/customers/{party_id}/tasks/{task_id}/done", response_class=HTMLResponse)
    async def handle_task_done_c360(request: Request, party_id: str, task_id: str) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        try:
            task_svc.transition_status(task_id, "done")
        except Exception as exc:
            log.error("c360: task done %s: %s", task_id, exc)
            return HTMLResponse("Lỗi cập nhật task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        return _render_tasks_panel(request, party_id, filter_val)

    @router.patch("/customers/{party_id}/tasks/{task_id}/cancel", response_class=HTMLResponse)
    async def handle_task_cancel_c360(request: Request, party_id: str, task_id: str) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        try:
            task_svc.transition_status(task_id, "cancelled")
        except Exception as exc:
            log.error("c360: task cancel %s: %s", task_id, exc)
            return HTMLResponse("Lỗi huỷ task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        return _render_tasks_panel(request, party_id, filter_val)

    @router.patch("/customers/{party_id}/tasks/{task_id}/postpone", response_class=HTMLResponse)
    async def handle_task_postpone_c360(
        request: Request,
        party_id: str,
        task_id: str,
        due_date: str = Form(default=""),
        due_time: str = Form(default=""),
    ) -> Response:
        if task_svc is None:
            return HTMLResponse("task service not available", status_code=503)
        if not due_date.strip():
            return HTMLResponse("Vui lòng chọn ngày", status_code=400)
        time_part = due_time.strip() or "09:00"
        new_due_at = _ict_local_to_utc(f"{due_date.strip()}T{time_part}")
        if not new_due_at:
            return HTMLResponse("Ngày không hợp lệ", status_code=400)
        try:
            t = task_svc.get_task(task_id)
            if t is not None and getattr(t, "status", "") == "doing":
                task_svc.transition_status(task_id, "open")
            task_svc.update_task(task_id, {"due_at": new_due_at})
        except Exception as exc:
            log.error("c360: task postpone %s: %s", task_id, exc)
            return HTMLResponse("Lỗi hoãn task", status_code=500)
        filter_val = request.query_params.get("filter", "open")
        return _render_tasks_panel(request, party_id, filter_val)

    @router.get("/modals/o03", response_class=HTMLResponse)
    async def handle_modal_o03(
        request: Request,
        task_id: str,
        party_id: str = "",
        due_at: str = "",
    ) -> Response:
        prefill_date = ""
        prefill_time = ""
        if due_at.strip():
            try:
                dt_utc = datetime.fromisoformat(due_at.strip().replace("Z", "+00:00"))
                dt_ict = dt_utc.astimezone(_ICT)
                prefill_date = dt_ict.strftime("%Y-%m-%d")
                prefill_time = dt_ict.strftime("%H:%M")
            except Exception:
                pass
        return templates.TemplateResponse(
            "fragments/overlay_o03_postpone_task.html",
            {
                "request": request,
                "task_id": task_id,
                "party_id": party_id,
                "due_at_prefill_date": prefill_date,
                "due_at_prefill_time": prefill_time,
            },
        )
