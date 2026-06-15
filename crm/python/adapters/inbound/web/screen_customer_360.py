"""Web adapter — S03 Customer 360 Detail screen.

FastAPI router mirroring screen_customer_360.go.
Serves full HTML page + HTMX panel fragments (panels: insight, orders,
timeline, tasks, notes). No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.python.domain.entities.activity import Activity
from crm.python.domain.entities.cache_insight import CacheInsight
from crm.python.domain.entities.profile import Note, Party360, PartyIdentity
from crm.python.domain.entities.task import Task

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────

class ProfileReader(Protocol):
    def get_party_360(self, party_id: str) -> Optional[Party360]: ...


class IdentityReader(Protocol):
    def list_identities(self, party_id: str) -> list[PartyIdentity]: ...


class InsightReader(Protocol):
    def get_customer_insight(self, customer_id: int) -> Optional[CacheInsight]: ...


class ActivityReader(Protocol):
    def list_timeline(self, party_id: str) -> list[Activity]: ...


class ActivityLogger(Protocol):
    def log_activity(self, a: Activity) -> None: ...


class NoteReader(Protocol):
    def add_note(self, party_id: str, body: str, author_user_id: Optional[str] = None) -> Note: ...
    def list_notes(self, party_id: str) -> list[Note]: ...


class TaskQuerier(Protocol):
    def list_by_party(self, party_id: str) -> list[Task]: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_customer_360_router(
    templates: Jinja2Templates,
    profile: ProfileReader,
    identities: IdentityReader,
    insight: InsightReader,
    activities: ActivityReader,
    activity_log: ActivityLogger,
    notes: NoteReader,
    party_tasks: TaskQuerier,
) -> APIRouter:
    """Return APIRouter wired with all Customer 360 routes."""
    router = APIRouter()

    def _load_base(party_id: str) -> tuple[Optional[Party360], list[PartyIdentity]]:
        party360 = profile.get_party_360(party_id)
        if party360 is None:
            return None, []
        ids = identities.list_identities(party_id)
        return party360, ids

    def _sapo_customer_id(party_id: str) -> int:
        """Resolve Sapo customer_id from party identities; 0 when not found."""
        try:
            for pid in identities.list_identities(party_id):
                if pid.identity_type == "sapo_customer":
                    return int(pid.identity_value)
        except Exception:
            pass
        return 0

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/customers/{party_id}", response_class=HTMLResponse)
    async def handle_customer_360(request: Request, party_id: str) -> Response:
        active_tab = request.query_params.get("tab", "insight")
        party360, ids = _load_base(party_id)
        if party360 is None:
            return HTMLResponse("Không tìm thấy khách hàng", status_code=404)
        return templates.TemplateResponse(
            "customer_360.html",
            {"request": request, "party": party360, "identities": ids, "active_tab": active_tab},
        )

    # ── HTMX panel fragments ──────────────────────────────────────────────────

    @router.get("/customers/{party_id}/panels/{panel}", response_class=HTMLResponse)
    async def handle_customer_360_panel(
        request: Request, party_id: str, panel: str
    ) -> Response:
        ctx: dict = {"request": request, "party_id": party_id}
        if panel == "insight":
            customer_id = _sapo_customer_id(party_id)
            ins = insight.get_customer_insight(customer_id) if customer_id else None
            return templates.TemplateResponse(
                "fragments/c360_insight_panel.html", {**ctx, "insight": ins}
            )
        if panel == "orders":
            customer_id = _sapo_customer_id(party_id)
            ins = insight.get_customer_insight(customer_id) if customer_id else None
            orders = ins.recent_orders if ins else []
            return templates.TemplateResponse(
                "fragments/c360_orders_panel.html", {**ctx, "orders": orders}
            )
        if panel == "timeline":
            acts = activities.list_timeline(party_id)
            return templates.TemplateResponse(
                "fragments/c360_timeline_panel.html", {**ctx, "activities": acts}
            )
        if panel == "tasks":
            task_list = party_tasks.list_by_party(party_id)
            return templates.TemplateResponse(
                "fragments/c360_tasks_panel.html", {**ctx, "tasks": task_list}
            )
        if panel == "notes":
            note_list = notes.list_notes(party_id)
            return templates.TemplateResponse(
                "fragments/c360_notes_panel.html", {**ctx, "notes": note_list}
            )
        return HTMLResponse("panel not found", status_code=404)

    # ── Note creation ─────────────────────────────────────────────────────────

    @router.post("/customers/{party_id}/notes", response_class=HTMLResponse)
    async def handle_add_note(
        request: Request, party_id: str, body: str = Form(...)
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("body required", status_code=400)
        try:
            note = notes.add_note(party_id, body)
        except Exception as exc:
            log.error("c360: add note %s: %s", party_id, exc)
            return HTMLResponse("failed to add note", status_code=500)
        return templates.TemplateResponse(
            "fragments/note_card.html", {"request": request, "note": note}
        )

    # ── Activity log (M08 modal) ──────────────────────────────────────────────

    @router.get("/customers/{party_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(request: Request, party_id: str) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            {"request": request, "party_id": party_id, "conv_id": ""},
        )

    @router.post("/customers/{party_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity(
        request: Request,
        party_id: str,
        activity_type: str = Form(default="note"),
        body: str = Form(...),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("body required", status_code=400)
        act = Activity(
            party_id=party_id,
            activity_type=activity_type or "note",
            body=body,
            channel="crm",
        )
        try:
            activity_log.log_activity(act)
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("failed to log activity", status_code=500)
        acts = activities.list_timeline(party_id)
        return templates.TemplateResponse(
            "fragments/c360_timeline_panel.html",
            {"request": request, "party_id": party_id, "activities": acts},
        )

    return router
