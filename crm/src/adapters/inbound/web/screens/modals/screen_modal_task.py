"""Web adapter — M05 Create / Edit Task modal.

Routes:
  GET   /modals/m05?party_id=&task_id=...   open the create/edit task modal
  PATCH /tasks/{task_id}/edit               save edits to an existing task
  POST  /customers/{party_id}/tasks         create a task for a party
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adapters.inbound.web.screens.modals.screen_modal_shared import (
    PRIO_INT_TO_STR,
    AppUserRepo,
    ProfileSvc,
    TaskSvc,
    parse_priority,
    redirect_to_customer,
)
from domain.entities.task import Task

log = logging.getLogger(__name__)


def make_task_modal_router(
    templates: Jinja2Templates,
    profile: ProfileSvc,
    task_svc: TaskSvc,
    app_users: AppUserRepo,
) -> APIRouter:
    router = APIRouter()

    @router.get("/modals/m05", response_class=HTMLResponse)
    async def get_modal_m05(
        request: Request,
        party_id: str = "",
        task_id: str = "",
        source: str = "",
        source_ref: str = "",
        prefill_title: str = "",
        prefill_priority: str = "",
    ) -> Response:
        au = []
        try:
            au = app_users.list_active()
        except Exception as exc:
            log.warning("m05: list_active: %s", exc)
        task: Optional[Task] = None
        if task_id:
            try:
                task = task_svc.get_task(task_id)
            except Exception as exc:
                log.warning("m05: get_task %s: %s", task_id, exc)
            if task and not party_id:
                party_id = task.party_id or ""
        # Resolve party name for the Khách hàng display field
        party_name = ""
        if party_id:
            try:
                p360 = profile.get_party_360(party_id)
                if p360:
                    party_name = p360.display_name
            except Exception as exc:
                log.debug("m05: get_party_360 %s: %s", party_id, exc)
        # Compute P-code for priority select
        if task:
            prio_code = PRIO_INT_TO_STR.get(task.priority, "P3")
        else:
            prio_code = "P2"  # prototype default for new tasks
        # Split due_at into date/time parts for the two inputs
        due_date_val = ""
        due_time_val = "10:00"
        if task and task.due_at:
            due_date_val = task.due_at[:10]
            if len(task.due_at) > 10:
                due_time_val = task.due_at[11:16]
        return templates.TemplateResponse(
            "fragments/modal_m05_create_task.html",
            {
                "request": request,
                "party_id": party_id,
                "party_name": party_name,
                "app_users": au,
                "task": task,
                "prefill_source": source,
                "prefill_source_ref": source_ref,
                "prefill_title": prefill_title,
                "prio_code": prio_code,
                "due_date_val": due_date_val,
                "due_time_val": due_time_val,
            },
        )

    @router.patch("/tasks/{task_id}/edit", response_class=HTMLResponse)
    async def patch_task_edit(
        request: Request,
        task_id: str,
        title: str = Form(...),
        description: str = Form(default=""),
        due_at: str = Form(default=""),
        priority: str = Form(default="P3"),
        assignee_user_id: str = Form(default=""),
        party_id: str = Form(default=""),
    ) -> Response:
        title = title.strip()
        if not title:
            return HTMLResponse("Tiêu đề không được bỏ trống", status_code=400)
        try:
            task_svc.update_task(task_id, {
                "title": title,
                "description": description.strip(),
                "due_at": due_at.strip() or None,
                "priority": parse_priority(priority),
                "assignee_user_id": assignee_user_id.strip() or None,
            })
        except Exception as exc:
            log.error("m05 edit task %s: %s", task_id, exc)
            return HTMLResponse("Lưu thất bại", status_code=500)
        redirect = f"/customers/{party_id}?tab=tasks" if party_id else "/tasks"
        return Response(status_code=200, headers={"HX-Redirect": redirect})

    @router.post("/customers/{party_id}/tasks", response_class=HTMLResponse)
    async def post_task(
        request: Request,
        party_id: str,
        title: str = Form(""),
        description: str = Form(""),
        due_at: str = Form(""),
        assignee_user_id: str = Form(""),
        priority: str = Form("P3"),
        source: str = Form("manual"),
        source_ref: str = Form(""),
    ) -> Response:
        title = title.strip()
        if not title:
            return HTMLResponse("Tiêu đề không được bỏ trống", status_code=400)
        current_user = getattr(request.state, "current_user", None)
        try:
            task_svc.create_task({
                "party_id": party_id,
                "title": title,
                "description": description.strip() or None,
                "due_at": due_at.strip() or None,
                "assignee_user_id": assignee_user_id.strip() or None,
                "priority": parse_priority(priority),
                "source": source.strip() or "manual",
                "source_ref": source_ref.strip() or None,
                "created_by": current_user.user_id if current_user else None,
            })
        except Exception as exc:
            log.error("post_task %s: %s", party_id, exc)
            return HTMLResponse(f"Lỗi tạo task: {exc}", status_code=500)
        return redirect_to_customer(party_id)

    return router
