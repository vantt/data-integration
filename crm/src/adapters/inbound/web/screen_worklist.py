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
    available_strategic_tiers,
    available_value_groups,
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
    def invalidate_cache(self) -> None: ...


class TaskQuerier(Protocol):
    def list_tasks(self, assignee_id: str, status: str) -> list[Task]: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...
    def list_unassigned(self, status: str) -> list[Task]: ...


class TaskWriter(Protocol):
    def transition_status(self, task_id: str, status: str) -> None: ...
    def assign_to(self, task_id: str, user_id: str) -> None: ...
    def update_task(self, task_id: str, data: dict) -> Task: ...


class ActionStateWriter(Protocol):
    def dismiss(self, action_id: str, user_id: Optional[str]) -> None: ...
    def snooze(self, action_id: str, until_date: str, user_id: Optional[str]) -> None: ...


class TaskClaimWriter(Protocol):
    def claim_customer_actions(self, party_id: str, actions: list, assignee_id: str) -> tuple: ...
    def unclaim_customer_actions(self, party_id: str) -> bool: ...


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
    task_claim: Optional[TaskClaimWriter] = None,
) -> APIRouter:
    """Return APIRouter wired with all Worklist routes."""
    router = APIRouter()

    def _load_worklist_data(
        filters: dict,
        current_user_id: str = "",
        script_cids: set | None = None,
    ) -> dict:
        """Fetch, filter, rank, and return everything the template needs.

        current_user_id scopes tasks to "mine" (assigned) + separate team queue
        (unassigned). When empty (no auth), my_tasks is empty and all open tasks
        fall into the team queue section.
        """
        try:
            all_actions = worklist_svc.list_all_action_queue()
        except Exception as exc:
            log.error("worklist: list actions: %s", exc)
            all_actions = []

        # my_tasks: tasks explicitly assigned to the current user → go into ranked bands
        try:
            my_tasks = tasks.list_tasks(current_user_id, "open") if current_user_id else []
        except Exception as exc:
            log.error("worklist: list my tasks: %s", exc)
            my_tasks = []

        # unassigned_tasks: team queue — no assignee, visible to all for self-assign
        try:
            unassigned_tasks = tasks.list_unassigned("open")
        except Exception as exc:
            log.error("worklist: list unassigned tasks: %s", exc)
            unassigned_tasks = []

        # Chips derive from unfiltered actions; text filter applied to both task lists
        available_types = available_action_types(all_actions)
        available_tiers = available_strategic_tiers(all_actions)
        available_value_groups_list = available_value_groups(all_actions)
        all_actions, my_tasks = apply_filters(all_actions, my_tasks, filters, script_cids)
        # Apply text/priority filter to unassigned queue too
        _, unassigned_tasks = apply_filters([], unassigned_tasks, filters, script_cids)
        all_tasks = my_tasks  # for legacy compat (counts, etc.)

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
            # Claim tasks whose party was recently contacted also belong in Band 4.
            # Their actions are hidden from all_actions by the SQL filter, so we
            # must check my_tasks directly to capture them.
            contacted_party_ids |= {
                t.party_id for t in my_tasks
                if t.party_id
                and getattr(t, "source", "") == "action_queue_claim"
                and _lc_age_seconds(t.party_id) <= 86400
            }

        # --- Rank into banded structure ------------------------------------
        today = today_ict()
        ranked = rank_worklist(all_actions, all_tasks, today, contacted_party_ids)

        # Build ordered list of action party_ids for call-mode queue (A2).
        # Computed before band slicing so all ranked action rows are included.
        # Capped at 50 to keep the query-string manageable.
        queue_party_ids: list[str] = []
        _seen_queue_pids: set[str] = set()
        for _band in ranked["bands"]:
            for _row in _band["rows"]:
                if _row.kind == "action":
                    _pid = getattr(_row.payload, "party_id", None)
                    if _pid and _pid not in _seen_queue_pids:
                        _seen_queue_pids.add(_pid)
                        queue_party_ids.append(str(_pid))
                        if len(queue_party_ids) >= 50:
                            break
            if len(queue_party_ids) >= 50:
                break

        # Screen adapter responsibility: cap band.rows to display_capacity before
        # passing to the template so the initial render only processes cap rows.
        # Overflow is loaded lazily via GET /worklist/band/{band_id}/more.
        # band.count retains the full count for the header badge.
        for band in ranked["bands"]:
            cap = band["display_capacity"]
            band["rows"] = band["rows"][:cap]

        return {
            **ranked,
            "party_extras": party_extras,
            "refreshed_at": refreshed_at,
            "is_stale": is_stale,
            "available_types": available_types,
            "active_filter_count": active_filter_count(filters),
            "filters": filters,
            "core_products": CORE_PRODUCTS,
            "available_tiers": available_tiers,
            "available_value_groups": available_value_groups_list,
            # script_cids: set[int] used by _wl_row template to badge actions that
            # have an approach script. Empty set when approach_repo is unavailable.
            "script_cids": script_cids if script_cids is not None else set(),
            # Pass raw lists for templates that might still iterate directly.
            "actions": all_actions,
            "tasks": all_tasks,
            # Team queue: unassigned tasks any user can pick up
            "unassigned_tasks": unassigned_tasks,
            "current_user_id": current_user_id,
            # A2: ordered party_ids for call-mode queue navigation (up to 50)
            "queue_party_ids": queue_party_ids,
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

    def _current_user_id(request: Request) -> str:
        user = getattr(request.state, "current_user", None)
        return user.user_id if user else ""

    @router.get("/", response_class=HTMLResponse)
    @router.get("/worklist", response_class=HTMLResponse)
    async def handle_worklist(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        script_cids = _get_script_cids(request)
        data = _load_worklist_data(filters, _current_user_id(request), script_cids)
        return templates.TemplateResponse(
            "worklist.html",
            {"request": request, **data, **filters},
        )

    async def _render_worklist_fragment(request: Request) -> Response:
        """Return the worklist fragment template; reads filters from form body or query params."""
        try:
            form = await request.form()
            # hx-include sends form data in PATCH body; fall back to query params for GET
            params = form if form else request.query_params
        except Exception:
            params = request.query_params
        filters = parse_filters(params)
        script_cids = _get_script_cids(request)
        data = _load_worklist_data(filters, _current_user_id(request), script_cids)
        return templates.TemplateResponse(
            "fragments/worklist_fragment.html",
            {"request": request, **data, **filters},
        )

    # ── HTMX fragment (refreshable inner container) ───────────────────────────

    @router.get("/worklist/fragment", response_class=HTMLResponse)
    async def handle_worklist_fragment(request: Request) -> Response:
        filters = parse_filters(request.query_params)
        script_cids = _get_script_cids(request)
        data = _load_worklist_data(filters, _current_user_id(request), script_cids)
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

    # ── Task snooze: shift due_at by N days (ICT-anchored) ───────────────
    # Resets status to "open" when task is "doing" so it re-enters the open queue.
    # Returns 204 (no content) — client uses hx-swap="none" and optionally refreshes.
    @router.patch("/tasks/{task_id}/snooze")
    async def handle_snooze_task(request: Request, task_id: str) -> Response:
        days_str = request.query_params.get("days", "1")
        try:
            days = max(1, min(int(days_str), 30))
        except ValueError:
            days = 1

        # ICT = UTC+7 (Asia/Ho_Chi_Minh); store as UTC midnight of the target day
        ict_offset = timezone(timedelta(hours=7))
        today_ict = datetime.now(ict_offset).date()
        new_due_date = today_ict + timedelta(days=days)
        new_due_utc = datetime(
            new_due_date.year, new_due_date.month, new_due_date.day,
            0, 0, 0, tzinfo=ict_offset,
        ).astimezone(timezone.utc)
        new_due_str = new_due_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            current_task = tasks.get_task(task_id)
            task_writer.update_task(task_id, {"due_at": new_due_str})
            # Reset status to open only if currently "doing"
            if current_task and current_task.status == "doing":
                task_writer.transition_status(task_id, "open")
        except Exception as exc:
            log.warning("snooze_task %s: %s", task_id, exc)
            return Response(status_code=500)

        return Response(status_code=204)

    # ── Self-assign from team queue ───────────────────────────────────────
    # Removes row client-side via hx-swap="delete" after assign succeeds.
    @router.patch("/tasks/{task_id}/assign-me", response_class=HTMLResponse)
    async def handle_assign_me(request: Request, task_id: str) -> Response:
        uid = _current_user_id(request)
        if not uid:
            return HTMLResponse("not authenticated", status_code=401)
        try:
            task_writer.assign_to(task_id, uid)
        except Exception as exc:
            log.error("worklist: assign-me task %s: %s", task_id, exc)
            return HTMLResponse("failed to assign", status_code=500)
        # Row disappears from team queue; page refresh picks it up in my tasks
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
        worklist_svc.invalidate_cache()
        # hx-swap="delete" on the client removes the row; return empty body
        return HTMLResponse("", status_code=200)

    # ── Action lifecycle: claim ("Nhận việc") ────────────────────────────
    # Creates a task linked to the action item, assigned to the current user.
    # The AND t.task_id IS NULL filter in cache_repository auto-hides the action
    # from WorkList once the task exists — no crm_action_state change needed.

    @router.patch("/worklist/actions/{action_id}/claim", response_class=HTMLResponse)
    async def handle_claim_action(request: Request, action_id: str) -> Response:
        """Claim ALL action items for the customer this action belongs to.

        One click claims the whole customer — multiple staff calling the same
        customer would disrupt them, so ownership is per-customer, not per-action.
        """
        uid = _current_user_id(request)
        if not uid:
            return HTMLResponse("Chưa đăng nhập", status_code=401)
        if task_claim is None:
            return HTMLResponse("", status_code=204)

        try:
            all_actions = worklist_svc.list_all_action_queue()
        except Exception as exc:
            log.error("worklist: claim: list_all_action_queue: %s", exc)
            all_actions = []

        action = next((a for a in all_actions if a.action_id == action_id), None)
        if action is None:
            # Stale action_id: already claimed by someone else (or TTL-cache/dbt
            # refresh moved it) between page render and click. Not an error —
            # re-render so the container reflects current truth instead of the
            # 200-body-swaps-outerHTML path wiping #worklist-container blank.
            return await _render_worklist_fragment(request)

        party_id = getattr(action, "party_id", None)
        if not party_id:
            log.warning("worklist: claim action %s has no resolvable party_id", action_id)
            # Non-2xx so htmx does not swap #worklist-container (same silent-failure
            # convention as the 401/500 branches below) — swapping a 200 here would
            # replace the whole container with just this notice, losing its id.
            return HTMLResponse(
                "Chưa xác định được khách hàng trong hệ thống", status_code=422
            )

        # Collect all action items for this customer (claim covers all of them)
        customer_actions = [a for a in all_actions if getattr(a, "party_id", None) == party_id]

        try:
            _task, is_new = task_claim.claim_customer_actions(party_id, customer_actions, uid)
        except Exception as exc:
            log.error("worklist: claim customer %s: %s", party_id, exc)
            return HTMLResponse("Không thể nhận việc", status_code=500)

        try:
            worklist_svc.invalidate_cache()
        except Exception as exc:
            log.warning("worklist: claim: invalidate_cache: %s", exc)

        return await _render_worklist_fragment(request)

    @router.patch("/worklist/customers/{party_id}/unclaim", response_class=HTMLResponse)
    async def handle_unclaim_customer(request: Request, party_id: str) -> Response:
        """Cancel the per-customer claim task, returning all their actions to the queue."""
        if task_claim is not None:
            try:
                task_claim.unclaim_customer_actions(party_id)
            except Exception as exc:
                log.error("worklist: unclaim customer %s: %s", party_id, exc)
        try:
            worklist_svc.invalidate_cache()
        except Exception as exc:
            log.warning("worklist: unclaim: invalidate_cache: %s", exc)
        return await _render_worklist_fragment(request)

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
        worklist_svc.invalidate_cache()
        return HTMLResponse("", status_code=200)

    # ── Band overflow: paginated lazy-load beyond display_capacity ───────
    # Triggered by HTMX on <details> toggle (_wl_bands.html) for the first page,
    # then by the "Xem thêm" button appended by _wl_overflow_rows.html for
    # subsequent pages. Page size is fixed at _OVERFLOW_PAGE rows.
    # Only the 20 rows being rendered are enriched — avoids a full party lookup.

    _OVERFLOW_PAGE = 20

    @router.get("/worklist/band/{band_id}/more", response_class=HTMLResponse)
    async def handle_band_overflow(request: Request, band_id: int) -> Response:
        filters = parse_filters(request.query_params)
        script_cids = _get_script_cids(request)

        try:
            offset = max(0, int(request.query_params.get("offset", "0")))
        except ValueError:
            offset = 0

        # Re-rank — action queue is TTL-cached, no DB hit
        all_actions = worklist_svc.list_all_action_queue()
        filtered_actions, _ = apply_filters(all_actions, [], filters, script_cids)

        contacted_party_ids: set = set()
        if not filters.get("hide_contacted"):
            overflow_party_ids = [a.party_id for a in filtered_actions if a.party_id]
            try:
                lc_map_overflow = worklist_svc.get_map_for_parties(overflow_party_ids)
                now_utc_overflow = datetime.now(timezone.utc)
                for pid, lc in lc_map_overflow.items():
                    try:
                        lc_dt = datetime.fromisoformat(
                            lc.last_contacted_at.replace("Z", "+00:00")
                        )
                        if (now_utc_overflow - lc_dt).total_seconds() <= 86400:
                            contacted_party_ids.add(pid)
                    except Exception:
                        pass
            except Exception as exc:
                log.warning("overflow: contacted_party_ids fetch: %s", exc)

        full_ranked = rank_worklist(filtered_actions, [], today_ict(), contacted_party_ids)
        full_band = next((b for b in full_ranked["bands"] if b["id"] == band_id), None)
        if full_band is None:
            return HTMLResponse("")

        all_rows = full_band["rows"]
        page_rows = all_rows[offset: offset + _OVERFLOW_PAGE]
        if not page_rows:
            return HTMLResponse("")

        next_offset = offset + _OVERFLOW_PAGE
        has_more = next_offset < len(all_rows)
        remaining = max(0, len(all_rows) - next_offset)

        # Enrich only parties visible on this page (not the full 4000)
        page_pids = list({getattr(r.payload, "party_id", None) for r in page_rows} - {None})
        party_extras: dict = {}
        if party_contacts is not None:
            for pid in page_pids:
                try:
                    pref = party_contacts.get_preferred_identity(pid)
                    cp_notes = party_contacts.list_pinned_contact_pref_notes(pid)
                    party_extras[pid] = {"preferred_identity": pref, "contact_pref_notes": cp_notes}
                except Exception as exc:
                    log.warning("overflow: enrich %s: %s", pid, exc)
        try:
            lc_map = worklist_svc.get_map_for_parties(page_pids)
            for pid, lc in lc_map.items():
                party_extras.setdefault(pid, {"preferred_identity": None, "contact_pref_notes": []})
                party_extras[pid]["last_contact"] = lc
        except Exception as exc:
            log.warning("overflow: last_contact: %s", exc)

        # Build next-page URL: carry filters, update offset
        qs_parts = [f"{k}={v}" for k, v in request.query_params.items() if k != "offset"]
        qs_parts.append(f"offset={next_offset}")
        next_url = f"/worklist/band/{band_id}/more?" + "&".join(qs_parts)

        return templates.TemplateResponse(
            "fragments/_wl_overflow_rows.html",
            {
                "request": request,
                "rows": page_rows,
                "party_extras": party_extras,
                "script_cids": script_cids,
                "has_more": has_more,
                "remaining": remaining,
                "next_url": next_url,
            },
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
