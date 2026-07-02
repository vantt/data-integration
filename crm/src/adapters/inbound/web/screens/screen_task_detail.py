"""Web adapter — S15 Task Detail screen.

GET  /tasks/{task_id}          — full task detail page (stub template)
POST /tasks/{task_id}/status   — lifecycle transition (start/cancel/reopen)

Templates are stubs (final markup via later ui-port step).
Context contract is authoritative — see phase-03-s15-task-detail-backend.md.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.task import Task, TASK_ALLOWED_TRANSITIONS, TASK_SOURCE_ACTION_QUEUE_CLAIM

log = logging.getLogger(__name__)


# ── Service protocols (duck-typed, no concrete imports) ───────────────────────

class TaskRepo(Protocol):
    def get_by_id(self, task_id: str) -> Optional[Task]: ...
    def list_by_party(self, party_id: str) -> list[Task]: ...


class ProfileReader(Protocol):
    def get_party_360(self, party_id: str) -> Optional[object]: ...


class IdentityReader(Protocol):
    def list_identities(self, party_id: str) -> list: ...


class InsightReader(Protocol):
    def get_customer_insight(self, customer_id: int) -> Optional[object]: ...


class ActivityReader(Protocol):
    def list_activities(self, party_id: str) -> list: ...


class TaskTransitioner(Protocol):
    def transition_status(self, task_id: str, new_status: str) -> object: ...
    def get_task(self, task_id: str) -> Optional[Task]: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_task_detail_router(
    templates: Jinja2Templates,
    task_repo: TaskRepo,
    profile: ProfileReader,
    identities: IdentityReader,
    insight: InsightReader,
    activities: ActivityReader,
    task_svc: TaskTransitioner,
) -> APIRouter:
    """Return APIRouter wired with S15 Task Detail routes."""
    router = APIRouter()

    def _sapo_customer_id(ids: list) -> int:
        for pid in ids:
            if getattr(pid, "identity_type", None) == "sapo_customer":
                try:
                    return int(pid.identity_value)
                except (ValueError, TypeError):
                    pass
        return 0

    def _resolve_provenance_action(task: Task, ins) -> Optional[object]:
        """Resolve the action_queue item backing this task's source_ref, or None."""
        if ins is None:
            return None
        if task.source not in (TASK_SOURCE_ACTION_QUEUE_CLAIM, "action_queue"):
            return None
        if not task.source_ref:
            return None
        for action in ins.actions:
            if getattr(action, "action_id", None) == task.source_ref:
                return action
        return None

    @router.get("/tasks/{task_id}", response_class=HTMLResponse)
    async def handle_task_detail(
        request: Request,
        task_id: str,
    ) -> Response:
        """Build S15 context and render stub template."""
        task = task_repo.get_by_id(task_id)
        if task is None:
            return HTMLResponse("Không tìm thấy task", status_code=404)

        allowed_transitions = TASK_ALLOWED_TRANSITIONS.get(task.status, [])
        body_kind = task.task_kind  # contact | internal | generic

        # Party data (only when task has a party_id)
        party = None
        task_identities: list = []
        ins = None
        attempt_log: list = []
        claim_actions: list = []
        provenance_action = None

        if task.party_id:
            try:
                party = profile.get_party_360(task.party_id)
            except Exception as exc:
                log.warning("s15: get_party_360 %s: %s", task.party_id, exc)

            try:
                task_identities = identities.list_identities(task.party_id)
            except Exception as exc:
                log.warning("s15: list_identities %s: %s", task.party_id, exc)

            # Load insight (cache-first; needed for provenance + claim_actions)
            customer_id = _sapo_customer_id(task_identities)
            if customer_id:
                try:
                    ins = insight.get_customer_insight(customer_id)
                except Exception as exc:
                    log.warning("s15: get_customer_insight %d: %s", customer_id, exc)

            # Attempt log — activities linked to this task (via task_id in activity data)
            try:
                all_acts = activities.list_activities(task.party_id)
                attempt_log = [
                    a for a in all_acts
                    if getattr(a, "task_id", None) == task_id
                ]
            except Exception as exc:
                log.warning("s15: list_activities %s: %s", task.party_id, exc)

            # Claim actions: if source=action_queue_claim, expose the customer's sorted action list
            if task.source == TASK_SOURCE_ACTION_QUEUE_CLAIM and ins is not None:
                claim_actions = ins.sorted_actions

            # Provenance action: resolve source_ref → action item
            provenance_action = _resolve_provenance_action(task, ins)

        return templates.TemplateResponse(
            "task_detail.html",
            {
                "request": request,
                "task": task,
                "party": party,
                "identities": task_identities,
                "insight": ins,
                "provenance_action": provenance_action,
                "attempt_log": attempt_log,
                "claim_actions": claim_actions,
                "allowed_transitions": allowed_transitions,
                "body_kind": body_kind,
            },
        )

    @router.post("/tasks/{task_id}/status", response_class=HTMLResponse)
    async def handle_task_status(
        request: Request,
        task_id: str,
        new_status: str = Form(...),
    ) -> Response:
        """Lifecycle transition endpoint (start→doing, cancel→cancelled, reopen).

        Validates transition against TASK_ALLOWED_TRANSITIONS before delegating
        to task_svc.transition_status (task_service.py — NOT edited here).
        """
        task = task_repo.get_by_id(task_id)
        if task is None:
            return HTMLResponse("Không tìm thấy task", status_code=404)

        allowed = TASK_ALLOWED_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            return HTMLResponse(
                f"Không thể chuyển từ '{task.status}' → '{new_status}'",
                status_code=422,
            )

        try:
            task_svc.transition_status(task_id, new_status)
        except Exception as exc:
            log.error("s15: transition_status %s → %s: %s", task_id, new_status, exc)
            return HTMLResponse("Lỗi cập nhật trạng thái task", status_code=500)

        # Redirect back to task detail after lifecycle change
        return HTMLResponse(
            content="",
            headers={"HX-Redirect": f"/tasks/{task_id}"},
        )

    return router
