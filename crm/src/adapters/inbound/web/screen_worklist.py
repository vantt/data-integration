"""Web adapter — S01 Worklist screen.

FastAPI router mirroring screen_worklist.go.
Serves full HTML page + HTMX-refreshable fragment + task-done PATCH.
Also handles action lifecycle: dismiss (PATCH /worklist/actions/{id}/dismiss)
and snooze (PATCH /worklist/actions/{id}/snooze?days=N).
No business logic — thin adapter only. All ranking delegated to worklist_ranking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from crm.src.domain.entities.last_contact import LastContact, POSITIVE_OUTCOMES

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.domain.entities.cache_insight import ActionQueueItem
from crm.src.domain.entities.profile import Note
from crm.src.domain.entities.party import PartyIdentity
from crm.src.domain.entities.task import Task
from crm.src.application.worklist_ranking import rank_worklist, today_ict
from crm.src.application.worklist_filters import (
    active_filter_count,
    apply_filters,
    available_action_types,
    parse_filters,
)

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────


class ActionQueueReader(Protocol):
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...


class TaskQuerier(Protocol):
    def list_tasks(self, assignee_id: str, status: str) -> list[Task]: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...


class TaskWriter(Protocol):
    def transition_status(self, task_id: str, status: str) -> None: ...


class ActionStateWriter(Protocol):
    def dismiss(self, action_id: str, user_id: Optional[str]) -> None: ...
    def snooze(self, action_id: str, until_date: str, user_id: Optional[str]) -> None: ...


class PartyContactReader(Protocol):
    def get_preferred_identity(self, party_id: str) -> Optional[PartyIdentity]: ...
    def list_pinned_contact_pref_notes(self, party_id: str) -> list[Note]: ...


class LastContactReader(Protocol):
    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]: ...


# ── Router factory ────────────────────────────────────────────────────────────


def make_worklist_router(
    templates: Jinja2Templates,
    action_queue: ActionQueueReader,
    tasks: TaskQuerier,
    task_writer: TaskWriter,
    action_state: Optional[ActionStateWriter] = None,
    party_contacts: Optional[PartyContactReader] = None,
    last_contact: Optional[LastContactReader] = None,
) -> APIRouter:
    """Return APIRouter wired with all Worklist routes."""
    router = APIRouter()

    def _load_worklist_data(filters: dict) -> dict:
        """Fetch, filter, rank, and return everything the template needs.

        Filters are applied before ranking so ranking only sees the relevant
        subset. Filter logic lives in the pure worklist_filters module.
        """
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

        # Chips derive from unfiltered data, then narrow the working set.
        available_types = available_action_types(all_actions)
        all_actions, all_tasks = apply_filters(all_actions, all_tasks, filters)

        # --- Metadata for freshness footer --------------------------------
        refreshed_at = ""
        is_stale = False
        if all_actions:
            refreshed_at = all_actions[0].refreshed_at
            is_stale = _is_cache_stale(refreshed_at)

        # --- Enrich party extras (contact pref, preferred identity) -------
        party_extras: dict = {}
        all_party_ids = list({
            *(a.party_id for a in all_actions if a.party_id),
            *(t.party_id for t in all_tasks if t.party_id),
        })
        if party_contacts is not None:
            for pid in all_party_ids:
                try:
                    pref = party_contacts.get_preferred_identity(pid)
                    cp_notes = party_contacts.list_pinned_contact_pref_notes(pid)
                    party_extras[pid] = {"preferred_identity": pref, "contact_pref_notes": cp_notes}
                except Exception as exc:
                    log.warning("worklist: enrich party %s: %s", pid, exc)

        # --- Merge last_contact snapshot into party_extras ----------------
        if last_contact is not None:
            try:
                lc_map = last_contact.get_map_for_parties(all_party_ids)
                for pid, lc in lc_map.items():
                    if pid not in party_extras:
                        party_extras[pid] = {"preferred_identity": None, "contact_pref_notes": []}
                    party_extras[pid]["last_contact"] = lc
            except Exception as exc:
                log.warning("worklist: last_contact fetch: %s", exc)

        # --- hide_contacted: suppress actions contacted in last 24h -------
        if filters.get("hide_contacted"):
            now_utc = datetime.now(timezone.utc)

            def _recently_contacted_positively(pid: str) -> bool:
                lc = party_extras.get(pid or "", {}).get("last_contact")
                if lc is None or lc.last_contact_result not in POSITIVE_OUTCOMES:
                    return False
                try:
                    lc_dt = datetime.fromisoformat(
                        lc.last_contacted_at.replace("Z", "+00:00")
                    )
                    return (now_utc - lc_dt).total_seconds() <= 86400
                except Exception:
                    return False

            all_actions = [a for a in all_actions
                           if not _recently_contacted_positively(a.party_id)]

        # --- Rank into banded structure ------------------------------------
        today = today_ict()
        ranked = rank_worklist(all_actions, all_tasks, today)

        return {
            **ranked,
            "party_extras": party_extras,
            "refreshed_at": refreshed_at,
            "is_stale": is_stale,
            "available_types": available_types,
            "active_filter_count": active_filter_count(filters),
            "filters": filters,
            # Pass raw lists for templates that might still iterate directly.
            "actions": all_actions,
            "tasks": all_tasks,
        }

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/", response_class=HTMLResponse)
    @router.get("/worklist", response_class=HTMLResponse)
    async def handle_worklist(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        data = _load_worklist_data(filters)
        return templates.TemplateResponse(
            "worklist.html",
            {"request": request, **data, **filters},
        )

    # ── HTMX fragment (refreshable inner container) ───────────────────────────

    @router.get("/worklist/fragment", response_class=HTMLResponse)
    async def handle_worklist_fragment(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        data = _load_worklist_data(filters)
        return templates.TemplateResponse(
            "fragments/worklist_fragment.html",
            {"request": request, **data, **filters},
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

    # ── Task cancel ("Dọn" on overdue rows) ───────────────────────────────
    # Worklist-local cancel: row is removed client-side via hx-swap="delete",
    # so an empty 200 body suffices (the c360 cancel route returns a full panel
    # and is not interchangeable here).
    @router.patch("/tasks/{task_id}/cancel", response_class=HTMLResponse)
    async def handle_cancel_task(request: Request, task_id: str) -> Response:
        try:
            task_writer.transition_status(task_id, "cancelled")
        except Exception as exc:
            log.error("worklist: cancel task %s: %s", task_id, exc)
            return HTMLResponse("failed to cancel task", status_code=500)
        return HTMLResponse("", status_code=200)

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
