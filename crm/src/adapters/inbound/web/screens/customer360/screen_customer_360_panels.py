"""Web adapter — Customer 360 HTMX panel fragment routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_panel_routes().
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.cache_insight import CustomerDimMetrics
from domain.entities.profile import PartyIdentity, PartyInsight

log = logging.getLogger(__name__)


def register_panel_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    activities,
    notes,
    party_tasks,
    party_insights=None,
    action_task_resolver=None,
    action_state=None,
    customer_timeline=None,
    customer_orders=None,
    customer_dim_metrics=None,
    app_users=None,
    approach_repo=None,
    _load_base,
    _load_insight,
    _sapo_customer_id,
) -> None:
    """Register HTMX panel fragment route on *router*."""

    @router.get("/customers/{party_id}/panels/{panel}", response_class=HTMLResponse)
    async def handle_customer_360_panel(
        request: Request, party_id: str, panel: str
    ) -> Response:
        ctx: dict = {"request": request, "party_id": party_id}
        if panel == "insight":
            _, ids = _load_base(party_id)
            ins = _load_insight(ids)
            rep_ins: list[PartyInsight] = []
            if party_insights is not None:
                try:
                    rep_ins = [
                        i for i in party_insights.list_by_party(party_id)
                        if not i.deleted_at
                    ]
                except Exception as exc:
                    log.warning("c360 insight panel: rep insights %s: %s", party_id, exc)
            resolved_ids: set[str] = set()
            if action_task_resolver is not None:
                try:
                    resolved_ids = action_task_resolver.resolved_action_ids(party_id)
                except Exception as exc:
                    log.warning("c360 insight panel: resolved_ids %s: %s", party_id, exc)
            dim_metrics: Optional[CustomerDimMetrics] = None
            if customer_dim_metrics is not None:
                sapo_id = _sapo_customer_id(ids)
                if sapo_id:
                    try:
                        dim_metrics = customer_dim_metrics.get_by_customer_id(sapo_id)
                    except Exception as exc:
                        log.warning("c360 insight panel: dim_metrics %s: %s", party_id, exc)
            snapshots: list = []
            timeline_available = customer_timeline is not None
            if customer_timeline is not None:
                sapo_id = _sapo_customer_id(ids)
                if sapo_id:
                    try:
                        snapshots = customer_timeline.get_by_customer_id(sapo_id)
                    except Exception as exc:
                        log.warning("c360 insight panel: snapshots %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_insight_panel.html",
                {**ctx, "insight": ins, "rep_insights": rep_ins, "resolved_action_ids": resolved_ids,
                 "dim_metrics": dim_metrics, "snapshots": snapshots, "timeline_available": timeline_available},
            )
        if panel == "orders":
            _, ids = _load_base(party_id)
            ins = _load_insight(ids)
            orders = ins.recent_orders if ins else []
            if customer_orders is not None:
                customer_id = _sapo_customer_id(ids)
                if customer_id:
                    try:
                        live = customer_orders.get_by_customer_id(customer_id)
                        if live:
                            orders = live
                    except Exception as exc:
                        log.warning("c360 orders panel: live fetch %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_orders_panel.html", {**ctx, "orders": orders}
            )
        if panel == "timeline":
            acts = activities.list_activities(party_id)
            tl_user_map: dict = {}
            if app_users is not None:
                try:
                    tl_user_map = {u.user_id: u.full_name for u in app_users.list_active()}
                except Exception as exc:
                    log.warning("c360 timeline: list_active: %s", exc)
            return templates.TemplateResponse(
                "fragments/c360_timeline_panel.html",
                {**ctx, "activities": acts, "user_map": tl_user_map},
            )
        if panel == "tasks":
            status_filter = request.query_params.get("filter", "open")
            task_list = party_tasks.list_by_party(party_id)
            user_map: dict = {}
            if app_users is not None:
                try:
                    user_map = {u.user_id: u.full_name for u in app_users.list_active()}
                except Exception as exc:
                    log.warning("c360 tasks: list_active: %s", exc)
            return templates.TemplateResponse(
                "fragments/c360_tasks_panel.html",
                {**ctx, "tasks": task_list, "filter": status_filter, "user_map": user_map,
                 "now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")},
            )
        if panel == "notes":
            note_list = notes.list_notes(party_id)
            type_filter = request.query_params.get("type_filter", "all")
            notes_user_map: dict = {}
            if app_users is not None:
                try:
                    notes_user_map = {u.user_id: u.full_name for u in app_users.list_active()}
                except Exception as exc:
                    log.warning("c360 notes: list_active: %s", exc)
            return templates.TemplateResponse(
                "fragments/c360_notes_panel.html",
                {**ctx, "notes": note_list, "type_filter": type_filter, "user_map": notes_user_map},
            )
        if panel == "call_cockpit":
            # Approach-script panel (S14 cockpit embedded in S03).
            # approach_repo is wired explicitly via make_customer_360_router (not app.state).
            _, ids = _load_base(party_id)
            customer_id = _sapo_customer_id(ids)
            script_dict = None
            meta_dict = None
            if customer_id and approach_repo is not None:
                try:
                    scr = approach_repo.get_by_customer_id(customer_id)
                    # Only render a script that carries the approach block; an
                    # approach-less dict would raise UndefinedError in the template.
                    if scr is not None and isinstance(scr.data, dict) and "approach" in scr.data:
                        script_dict = scr.data
                        meta_dict = {"recommended": scr.recommended,
                                     "confidence": scr.confidence,
                                     "refreshed_at": scr.refreshed_at}
                except Exception as exc:
                    log.warning("c360 call_cockpit: load script %s: %s", party_id, exc)
            return templates.TemplateResponse(
                "fragments/c360_call_cockpit_panel.html",
                {**ctx, "script": script_dict, "meta": meta_dict},
            )
        return HTMLResponse("panel not found", status_code=404)

    # ── Bulk-dismiss action session ───────────────────────────────────────────

    @router.post("/customers/{party_id}/actions/dismiss-session", response_class=HTMLResponse)
    async def handle_dismiss_session(request: Request, party_id: str) -> Response:
        """Dismiss multiple action_ids in one session, return refreshed insight panel."""
        if action_state is not None:
            form = await request.form()
            action_ids = form.getlist("action_ids")
            for aid in action_ids:
                try:
                    action_state.dismiss(aid, user_id=None)
                except Exception as exc:
                    log.error("c360: dismiss action %s: %s", aid, exc)
        _, ids = _load_base(party_id)
        ins = _load_insight(ids)
        resolved_ids: set[str] = set()
        if action_task_resolver is not None:
            try:
                resolved_ids = action_task_resolver.resolved_action_ids(party_id)
            except Exception as exc:
                log.warning("c360: dismiss-session resolved_ids %s: %s", party_id, exc)
        rep_ins: list = []
        if party_insights is not None:
            try:
                rep_ins = [i for i in party_insights.list_by_party(party_id) if not i.deleted_at]
            except Exception as exc:
                log.warning("c360: dismiss-session rep_ins %s: %s", party_id, exc)
        return templates.TemplateResponse(
            "fragments/c360_insight_panel.html",
            {"request": request, "party_id": party_id, "insight": ins,
             "rep_insights": rep_ins, "resolved_action_ids": resolved_ids,
             "dim_metrics": None, "snapshots": [], "timeline_available": False},
        )
