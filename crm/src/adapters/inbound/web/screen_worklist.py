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

from domain.entities.last_contact import LastContact, POSITIVE_OUTCOMES

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.cache_insight import ActionQueueItem
from domain.entities.profile import Note
from domain.entities.party import PartyIdentity
from domain.entities.task import Task
from application.worklist_ranking import rank_worklist, today_ict
from application.worklist_filters import (
    CORE_PRODUCTS,
    active_filter_count,
    apply_filters,
    available_action_types,
    parse_filters,
)

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────


class WorklistSvc(Protocol):
    """Interface satisfied by WorklistQueryService.

    Screens depend on this protocol, not on the concrete service or repos
    directly, so the service can be swapped or extended without touching
    the screen layer.
    """
    def list_all_action_queue(self) -> list[ActionQueueItem]: ...
    def get_map_for_parties(self, party_ids: list[str]) -> dict[str, LastContact]: ...


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


# ── Router factory ────────────────────────────────────────────────────────────


def make_worklist_router(
    templates: Jinja2Templates,
    worklist_svc: WorklistSvc,
    tasks: TaskQuerier,
    task_writer: TaskWriter,
    action_state: Optional[ActionStateWriter] = None,
    party_contacts: Optional[PartyContactReader] = None,
) -> APIRouter:
    """Return APIRouter wired with all Worklist routes."""
    router = APIRouter()

    def _load_worklist_data(filters: dict, script_cids: set | None = None) -> dict:
        """Fetch, filter, rank, and return everything the template needs.

        Filters are applied before ranking so ranking only sees the relevant
        subset. Filter logic lives in the pure worklist_filters module.

        script_cids: set[int] of customer_ids with an approach script, computed
        once per request by the route handler from approach_repo.list_customer_ids().
        """
        try:
            all_actions = worklist_svc.list_all_action_queue()
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
        all_actions, all_tasks = apply_filters(all_actions, all_tasks, filters, script_cids)

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
        try:
            lc_map = worklist_svc.get_map_for_parties(all_party_ids)
            for pid, lc in lc_map.items():
                if pid not in party_extras:
                    party_extras[pid] = {"preferred_identity": None, "contact_pref_notes": []}
                party_extras[pid]["last_contact"] = lc
        except Exception as exc:
            log.warning("worklist: last_contact fetch: %s", exc)

        # --- Identify recently-contacted parties for band 4 + hide filter -------
        # Band 4 ("Đã liên hệ"): ANY contact attempt in last 24h (regardless of outcome)
        #   so the agent can see what they already tried today.
        # hide_contacted filter: only removes POSITIVE outcomes (answered/replied/met) —
        #   unresolved attempts (no_answer) stay visible since the agent may retry.
        now_utc = datetime.now(timezone.utc)

        def _lc_age_seconds(pid: str) -> float:
            """Return seconds since last contact for pid, or inf when unavailable."""
            lc = party_extras.get(pid or "", {}).get("last_contact")
            if lc is None:
                return float("inf")
            try:
                lc_dt = datetime.fromisoformat(
                    lc.last_contacted_at.replace("Z", "+00:00")
                )
                return (now_utc - lc_dt).total_seconds()
            except Exception:
                return float("inf")

        def _lc_result(pid: str) -> str:
            lc = party_extras.get(pid or "", {}).get("last_contact")
            return lc.last_contact_result if lc else ""

        if filters.get("hide_contacted"):
            # Remove POSITIVE-outcome contacts from the list entirely.
            all_actions = [
                a for a in all_actions
                if not (
                    _lc_age_seconds(a.party_id) <= 86400
                    and _lc_result(a.party_id) in POSITIVE_OUTCOMES
                )
            ]
            contacted_party_ids: set = set()
        else:
            # Move ALL recent contacts (any outcome) to band 4.
            contacted_party_ids = {
                a.party_id for a in all_actions
                if a.party_id and _lc_age_seconds(a.party_id) <= 86400
            }

        # --- Rank into banded structure ------------------------------------
        today = today_ict()
        ranked = rank_worklist(all_actions, all_tasks, today, contacted_party_ids)

        return {
            **ranked,
            "party_extras": party_extras,
            "refreshed_at": refreshed_at,
            "is_stale": is_stale,
            "available_types": available_types,
            "active_filter_count": active_filter_count(filters),
            "filters": filters,
            "core_products": CORE_PRODUCTS,
            # script_cids: set[int] used by _wl_row template to badge actions that
            # have an approach script. Empty set when approach_repo is unavailable.
            "script_cids": script_cids if script_cids is not None else set(),
            # Pass raw lists for templates that might still iterate directly.
            "actions": all_actions,
            "tasks": all_tasks,
        }

    # ── Full page ─────────────────────────────────────────────────────────────

    def _get_script_cids(request: Request) -> set:
        """Fetch script customer_id set from approach_repo; empty set on error."""
        approach_repo = getattr(request.app.state, "approach_repo", None)
        if approach_repo is None:
            return set()
        try:
            return approach_repo.list_customer_ids()
        except Exception as exc:
            log.warning("worklist: list_customer_ids failed: %s", exc)
            return set()

    @router.get("/", response_class=HTMLResponse)
    @router.get("/worklist", response_class=HTMLResponse)
    async def handle_worklist(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        script_cids = _get_script_cids(request)
        data = _load_worklist_data(filters, script_cids)
        return templates.TemplateResponse(
            "worklist.html",
            {"request": request, **data, **filters},
        )

    # ── HTMX fragment (refreshable inner container) ───────────────────────────

    @router.get("/worklist/fragment", response_class=HTMLResponse)
    async def handle_worklist_fragment(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        script_cids = _get_script_cids(request)
        data = _load_worklist_data(filters, script_cids)
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
