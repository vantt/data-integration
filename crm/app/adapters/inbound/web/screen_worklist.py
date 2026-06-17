"""Web adapter — S01 Worklist screen.

FastAPI router mirroring screen_worklist.go.
Serves full HTML page + HTMX-refreshable fragment + task-done PATCH.
Also handles action lifecycle: dismiss (PATCH /worklist/actions/{id}/dismiss)
and snooze (PATCH /worklist/actions/{id}/snooze?days=N).
No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.app.domain.entities.cache_insight import ActionQueueItem
from crm.app.domain.entities.profile import Note
from crm.app.domain.entities.party import PartyIdentity
from crm.app.domain.entities.task import Task

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────


class ActionQueueReader(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...


class TaskQuerier(Protocol):
    def list_tasks(self, party_id: str, status: str) -> list[Task]: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...


class TaskWriter(Protocol):
    def transition_status(self, task_id: str, status: str) -> None: ...


class ActionStateWriter(Protocol):
    def dismiss(self, action_id: str, user_id: Optional[str]) -> None: ...
    def snooze(self, action_id: str, until_date: str, user_id: Optional[str]) -> None: ...


class PartyContactReader(Protocol):
    def get_preferred_identity(self, party_id: str) -> Optional[PartyIdentity]: ...
    def list_pinned_contact_pref_notes(self, party_id: str) -> list[Note]: ...


# ── Router factory ────────────────────────────────────────────────────────────


def make_worklist_router(
    templates: Jinja2Templates,
    action_queue: ActionQueueReader,
    tasks: TaskQuerier,
    task_writer: TaskWriter,
    action_state: Optional[ActionStateWriter] = None,
    party_contacts: Optional[PartyContactReader] = None,
) -> APIRouter:
    """Return APIRouter wired with all Worklist routes."""
    router = APIRouter()

    def _load_worklist_data(
        filter_assignee: str = "me",
        filter_priority: str = "all",
    ) -> tuple[list[ActionQueueItem], list[Task], str, bool, dict]:
        try:
            all_actions = action_queue.list_all_action_queue()
        except Exception as exc:
            log.error("worklist: list actions: %s", exc)
            all_actions = []

        try:
            all_tasks = tasks.list_tasks("", "open")
        except Exception as exc:
            log.error("worklist: list tasks: %s", exc)
            all_tasks = []

        # Apply priority filter (int: 0=normal, higher=more urgent; high>=3, urgent>=4)
        if filter_priority == "urgent":
            all_tasks = [t for t in all_tasks if t.priority >= 4]
        elif filter_priority == "high":
            all_tasks = [t for t in all_tasks if t.priority >= 3]

        refreshed_at = ""
        is_stale = False
        if all_actions:
            refreshed_at = all_actions[0].refreshed_at
            is_stale = _is_cache_stale(refreshed_at)

        # Batch-load contact_pref notes + preferred identity per party
        party_extras: dict = {}
        if party_contacts is not None:
            seen: set[str] = set()
            party_ids = [a.party_id for a in all_actions if a.party_id]
            party_ids += [t.party_id for t in all_tasks if t.party_id]
            for pid in party_ids:
                if pid in seen:
                    continue
                seen.add(pid)
                try:
                    pref = party_contacts.get_preferred_identity(pid)
                    cp_notes = party_contacts.list_pinned_contact_pref_notes(pid)
                    party_extras[pid] = {"preferred_identity": pref, "contact_pref_notes": cp_notes}
                except Exception as exc:
                    log.warning("worklist: enrich party %s: %s", pid, exc)

        return all_actions, all_tasks, refreshed_at, is_stale, party_extras

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/", response_class=HTMLResponse)
    @router.get("/worklist", response_class=HTMLResponse)
    async def handle_worklist(request: Request) -> Response:
        fa = request.query_params.get("assignee", "me")
        fp = request.query_params.get("priority", "all")
        actions, task_list, refreshed_at, is_stale, party_extras = _load_worklist_data(fa, fp)
        return templates.TemplateResponse(
            "worklist.html",
            {
                "request": request,
                "actions": actions,
                "tasks": task_list,
                "refreshed_at": refreshed_at,
                "is_stale": is_stale,
                "party_extras": party_extras,
                "filter_assignee": fa,
                "filter_priority": fp,
            },
        )

    # ── HTMX fragment (refreshable inner container) ───────────────────────────

    @router.get("/worklist/fragment", response_class=HTMLResponse)
    async def handle_worklist_fragment(request: Request) -> Response:
        fa = request.query_params.get("assignee", "me")
        fp = request.query_params.get("priority", "all")
        actions, task_list, refreshed_at, is_stale, party_extras = _load_worklist_data(fa, fp)
        return templates.TemplateResponse(
            "fragments/worklist_fragment.html",
            {
                "request": request,
                "actions": actions,
                "tasks": task_list,
                "refreshed_at": refreshed_at,
                "is_stale": is_stale,
                "party_extras": party_extras,
                "filter_assignee": fa,
                "filter_priority": fp,
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

    # ── Action lifecycle: dismiss ─────────────────────────────────────────

    @router.patch("/worklist/actions/{action_id}/dismiss", response_class=HTMLResponse)
    async def handle_dismiss_action(request: Request, action_id: str) -> Response:
        if action_state is None:
            return HTMLResponse("", status_code=204)
        try:
            action_state.dismiss(action_id, user_id=None)
        except Exception as exc:
            log.error("worklist: dismiss action %s: %s", action_id, exc)
            return HTMLResponse("failed", status_code=500)
        # hx-swap="delete" on the client removes the row; return empty body
        return HTMLResponse("", status_code=200)

    # ── Action lifecycle: snooze ──────────────────────────────────────────

    @router.patch("/worklist/actions/{action_id}/snooze", response_class=HTMLResponse)
    async def handle_snooze_action(request: Request, action_id: str) -> Response:
        if action_state is None:
            return HTMLResponse("", status_code=204)
        try:
            days = int(request.query_params.get("days", "3"))
            days = max(1, min(days, 30))  # clamp to sensible range
            until_date = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
            action_state.snooze(action_id, until_date, user_id=None)
        except Exception as exc:
            log.error("worklist: snooze action %s: %s", action_id, exc)
            return HTMLResponse("failed", status_code=500)
        return HTMLResponse("", status_code=200)

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
