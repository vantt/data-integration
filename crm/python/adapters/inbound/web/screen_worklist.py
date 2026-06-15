"""Web adapter — S01 Worklist screen.

FastAPI router mirroring screen_worklist.go.
Serves full HTML page + HTMX-refreshable fragment + task-done PATCH.
No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Protocol

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.python.domain.entities.cache_insight import ActionQueueItem
from crm.python.domain.entities.task import Task

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────


class ActionQueueReader(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...


class TaskQuerier(Protocol):
    def list_tasks(self, party_id: str, status: str) -> list[Task]: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...


class TaskWriter(Protocol):
    def transition_status(self, task_id: str, status: str) -> None: ...


# ── Router factory ────────────────────────────────────────────────────────────


def make_worklist_router(
    templates: Jinja2Templates,
    action_queue: ActionQueueReader,
    tasks: TaskQuerier,
    task_writer: TaskWriter,
) -> APIRouter:
    """Return APIRouter wired with all Worklist routes."""
    router = APIRouter()

    def _load_worklist_data() -> tuple[list[ActionQueueItem], list[Task], str, bool]:
        try:
            actions = action_queue.list_all_action_queue()
        except Exception as exc:
            log.error("worklist: list actions: %s", exc)
            actions = []

        try:
            task_list = tasks.list_tasks("", "open")
        except Exception as exc:
            log.error("worklist: list tasks: %s", exc)
            task_list = []

        refreshed_at = ""
        is_stale = False
        if actions:
            refreshed_at = actions[0].refreshed_at
            is_stale = _is_cache_stale(refreshed_at)

        return actions, task_list, refreshed_at, is_stale

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/", response_class=HTMLResponse)
    @router.get("/worklist", response_class=HTMLResponse)
    async def handle_worklist(request: Request) -> Response:
        actions, task_list, refreshed_at, is_stale = _load_worklist_data()
        return templates.TemplateResponse(
            "worklist.html",
            {
                "request": request,
                "actions": actions,
                "tasks": task_list,
                "refreshed_at": refreshed_at,
                "is_stale": is_stale,
            },
        )

    # ── HTMX fragment (refreshable inner container) ───────────────────────────

    @router.get("/worklist/fragment", response_class=HTMLResponse)
    async def handle_worklist_fragment(request: Request) -> Response:
        actions, task_list, refreshed_at, is_stale = _load_worklist_data()
        return templates.TemplateResponse(
            "fragments/worklist_fragment.html",
            {
                "request": request,
                "actions": actions,
                "tasks": task_list,
                "refreshed_at": refreshed_at,
                "is_stale": is_stale,
            },
        )

    # ── HTMX task-done PATCH ──────────────────────────────────────────────────

    @router.patch("/tasks/{task_id}/done", response_class=HTMLResponse)
    async def handle_mark_task_done(request: Request, task_id: str) -> Response:
        try:
            task_writer.transition_status(task_id, "done")
        except Exception as exc:
            log.error("worklist: mark done %s: %s", task_id, exc)
            return HTMLResponse("failed to update task", status_code=500)

        try:
            task = tasks.get_task(task_id)
        except Exception:
            task = None

        if task is None:
            from html import escape
            html = (
                f'<div class="task-row done" id="task-{escape(task_id)}">'
                '<span class="text-muted">✓ Đã hoàn thành</span></div>'
            )
            return HTMLResponse(html)

        return templates.TemplateResponse(
            "fragments/task_done_row.html",
            {"request": request, "task": task},
        )

    return router


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _is_cache_stale(utc_iso: str) -> bool:
    """Return True when the UTC ISO-8601 timestamp is older than 24 h."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(utc_iso, fmt).replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).total_seconds() > 86400
        except ValueError:
            continue
    return False
