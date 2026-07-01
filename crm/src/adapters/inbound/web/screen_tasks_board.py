"""Web adapter — S07 Tasks Board screen.

FastAPI router mirroring screen_tasks_board.go.
Serves full Kanban HTML page + HTMX status-transition endpoint.
No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.task import Task, VALID_TASK_STATUSES

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────

class TaskQuerier(Protocol):
    def list_tasks(self, assignee: str, status: str) -> list[Task]: ...


class UserQuerier(Protocol):
    def list_active(self) -> list: ...


class TaskWriter(Protocol):
    def transition_status(self, task_id: str, new_status: str) -> None: ...


class TaskCreator(Protocol):
    def create_task(self, task_data: dict) -> object: ...


class TaskGenerator(Protocol):
    def generate_tasks_from_action_queue(self) -> int: ...


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_by_status(tasks: list[Task]) -> dict[str, list[Task]]:
    """Partition tasks into kanban columns: open / doing / done / cancelled."""
    grouped: dict[str, list[Task]] = {
        "open": [], "doing": [], "done": [], "cancelled": [],
    }
    for t in tasks:
        bucket = t.status if t.status in grouped else "open"
        grouped[bucket].append(t)
    return grouped


def _task_status_css(status: str) -> str:
    return {
        "open": "bdg--good",
        "doing": "bdg--warn",
        "done": "",
        "cancelled": "bdg--off",
    }.get(status, "")


# ── Router factory ────────────────────────────────────────────────────────────

def make_tasks_board_router(
    templates: Jinja2Templates,
    task_querier: TaskQuerier,
    task_writer: TaskWriter,
    task_creator: TaskCreator,
    task_generator: Optional[TaskGenerator] = None,
    user_querier: Optional[UserQuerier] = None,
) -> APIRouter:
    """Return APIRouter wired with all Tasks Board routes."""
    router = APIRouter()

    @router.get("/tasks", response_class=HTMLResponse)
    async def handle_tasks_board(request: Request) -> Response:
        assignee = request.query_params.get("assignee", "")
        status_filter = request.query_params.get("status", "")
        try:
            tasks = task_querier.list_tasks(assignee, status_filter)
        except Exception as exc:
            log.error("tasks board: list: %s", exc)
            tasks = []
        users = user_querier.list_active() if user_querier else []
        grouped = _group_by_status(tasks)
        return templates.TemplateResponse(
            "tasks_board.html",
            {
                "request": request,
                "grouped": grouped,
                "assignee_filter": assignee,
                "status_filter": status_filter,
                "task_status_css": _task_status_css,
                "users": users,
            },
        )

    @router.get("/tasks/modal/create", response_class=HTMLResponse)
    async def handle_modal_create_task(request: Request) -> Response:
        party_id = request.query_params.get("party_id", "")
        return templates.TemplateResponse(
            "fragments/modal_create_task.html",
            {"request": request, "party_id": party_id},
        )

    @router.post("/tasks", response_class=HTMLResponse)
    async def handle_create_task(
        request: Request,
        title: str = Form(...),
        description: str = Form(default=""),
        due_at: str = Form(default=""),
        party_id: str = Form(default=""),
        assignee_user_id: str = Form(default=""),
    ) -> Response:
        title = title.strip()
        if not title:
            return HTMLResponse("title required", status_code=400)
        current_user = getattr(request.state, "current_user", None)
        task_data = {
            "title": title,
            "description": description.strip() or None,
            "status": "open",
            "source": "manual",
            "priority": 0,
            "due_at": due_at.strip() or None,
            "party_id": party_id.strip() or None,
            "assignee_user_id": assignee_user_id.strip() or None,
            "created_by": current_user.user_id if current_user else None,
        }
        try:
            task_creator.create_task(task_data)
        except Exception as exc:
            log.error("create task: %s", exc)
            return HTMLResponse("failed to create task", status_code=500)
        return Response(
            status_code=200,
            headers={"HX-Trigger": '{"closeModal":true}', "HX-Redirect": "/tasks"},
        )

    @router.patch("/tasks/{task_id}/status", response_class=HTMLResponse)
    async def handle_task_status_transition(
        request: Request, task_id: str, status: str = Form(...)
    ) -> Response:
        status = status.strip()
        if status not in VALID_TASK_STATUSES:
            return HTMLResponse("invalid status", status_code=400)
        try:
            task_writer.transition_status(task_id, status)
        except Exception as exc:
            log.error("task status transition %s→%s: %s", task_id, status, exc)
            return HTMLResponse("failed to transition", status_code=500)
        return Response(status_code=200, headers={"HX-Redirect": "/tasks"})

    @router.post("/tasks/generate", response_class=HTMLResponse)
    async def handle_generate_tasks_from_queue(request: Request) -> Response:
        if task_generator is None:
            return Response(status_code=200, headers={"HX-Redirect": "/tasks"})
        try:
            count = task_generator.generate_tasks_from_action_queue()
            log.info("generate tasks from queue: created %d tasks", count)
        except Exception as exc:
            log.error("generate tasks from queue: %s", exc)
        return Response(status_code=200, headers={"HX-Redirect": "/tasks"})

    return router
