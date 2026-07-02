"""Web adapter — Customer 360 HTMX panel fragment routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_panel_routes().
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from application.geography import geo_region
from application.reason_rail import assemble_reason_rail
from domain.entities.cache_insight import CustomerDimMetrics
from domain.entities.profile import PartyIdentity, PartyInsight
from domain.entities.task import TASK_KIND_CONTACT, TASK_STATUS_OPEN, TASK_STATUS_DOING

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
    claimed_action_resolver=None,
    task_svc=None,
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

    async def _render_insight_panel_response(request: Request, party_id: str) -> Response:
        """Render the full insight panel; shared by GET panel + claim/unclaim endpoints."""
        ctx: dict = {"request": request, "party_id": party_id}
        _, ids = _load_base(party_id)
        ins = _load_insight(ids)
        rep_ins: list = []
        if party_insights is not None:
            try:
                rep_ins = [i for i in party_insights.list_by_party(party_id) if not i.deleted_at]
            except Exception as exc:
                log.warning("c360 insight render: rep_ins %s: %s", party_id, exc)
        resolved_ids: set[str] = set()
        if action_task_resolver is not None:
            try:
                resolved_ids = action_task_resolver.resolved_action_ids(party_id)
            except Exception as exc:
                log.warning("c360 insight render: resolved_ids %s: %s", party_id, exc)
        customer_claim: Optional[dict] = None
        if claimed_action_resolver is not None:
            try:
                customer_claim = claimed_action_resolver.get_customer_claim_info(party_id)
            except Exception as exc:
                log.warning("c360 insight render: customer_claim %s: %s", party_id, exc)
        dim_metrics: Optional[CustomerDimMetrics] = None
        snapshots: list = []
        timeline_available = customer_timeline is not None
        sapo_id = _sapo_customer_id(ids)
        if sapo_id and (customer_dim_metrics is not None or customer_timeline is not None):
            coros = []
            run_dim = customer_dim_metrics is not None
            run_tl = customer_timeline is not None
            if run_dim:
                coros.append(asyncio.to_thread(customer_dim_metrics.get_by_customer_id, sapo_id))
            if run_tl:
                coros.append(asyncio.to_thread(customer_timeline.get_by_customer_id, sapo_id))
            results = await asyncio.gather(*coros, return_exceptions=True)
            idx = 0
            if run_dim:
                r = results[idx]; idx += 1
                if isinstance(r, Exception):
                    log.warning("c360 insight render: dim_metrics %s: %s", party_id, r)
                else:
                    dim_metrics = r
            if run_tl:
                r = results[idx]
                if isinstance(r, Exception):
                    log.warning("c360 insight render: snapshots %s: %s", party_id, r)
                else:
                    snapshots = r or []
        return templates.TemplateResponse(
            "fragments/c360_insight_panel.html",
            {**ctx, "insight": ins, "rep_insights": rep_ins,
             "resolved_action_ids": resolved_ids, "customer_claim": customer_claim,
             "dim_metrics": dim_metrics, "snapshots": snapshots,
             "timeline_available": timeline_available},
        )

    @router.patch("/customers/{party_id}/claim", response_class=HTMLResponse)
    async def handle_c360_claim_customer(
        request: Request, party_id: str
    ) -> Response:
        """Claim all action items for a customer from C360."""
        uid = getattr(getattr(request.state, "current_user", None), "user_id", "")
        if not uid:
            return HTMLResponse("", status_code=401)
        if task_svc is not None:
            try:
                _, ids = _load_base(party_id)
                ins = _load_insight(ids)
                actions = ins.actions if ins else []
                task_svc.claim_customer_actions(party_id, actions, uid)
            except Exception as exc:
                log.error("c360: claim customer %s: %s", party_id, exc)
        return await _render_insight_panel_response(request, party_id)

    @router.patch("/customers/{party_id}/unclaim", response_class=HTMLResponse)
    async def handle_c360_unclaim_customer(
        request: Request, party_id: str
    ) -> Response:
        """Cancel the per-customer claim task from C360."""
        if task_svc is not None:
            try:
                task_svc.unclaim_customer_actions(party_id)
            except Exception as exc:
                log.error("c360: unclaim customer %s: %s", party_id, exc)
        return await _render_insight_panel_response(request, party_id)

    @router.get("/customers/{party_id}/panels/{panel}", response_class=HTMLResponse)
    async def handle_customer_360_panel(
        request: Request, party_id: str, panel: str
    ) -> Response:
        ctx: dict = {"request": request, "party_id": party_id}
        if panel == "insight":
            return await _render_insight_panel_response(request, party_id)
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
            # ── S14 v2: enriched cockpit context (phase-04) ─────────────────
            # approach_repo wired via make_customer_360_router (not app.state).
            party, ids = _load_base(party_id)
            customer_id = _sapo_customer_id(ids)
            ins = _load_insight(ids)

            script_dict = None
            meta_dict = None
            if customer_id and approach_repo is not None:
                try:
                    scr = approach_repo.get_by_customer_id(customer_id)
                    # Only render a script that carries the approach block.
                    if scr is not None and isinstance(scr.data, dict) and "approach" in scr.data:
                        script_dict = scr.data
                        meta_dict = {"recommended": scr.recommended,
                                     "confidence": scr.confidence,
                                     "refreshed_at": scr.refreshed_at}
                except Exception as exc:
                    log.warning("c360 call_cockpit: load script %s: %s", party_id, exc)

            # Warning notes
            warning_notes: list = []
            if notes is not None:
                try:
                    all_notes = notes.list_notes(party_id)
                    warning_notes = [
                        n for n in all_notes
                        if not n.deleted_at and n.note_type == "warning"
                    ]
                except Exception as exc:
                    log.warning("c360 call_cockpit: warning_notes %s: %s", party_id, exc)

            # Resolved action_ids
            resolved_ids: set = set()
            if action_task_resolver is not None:
                try:
                    resolved_ids = action_task_resolver.resolved_action_ids(party_id)
                except Exception as exc:
                    log.warning("c360 call_cockpit: resolved_ids %s: %s", party_id, exc)

            # Contact tasks for reason rail (open + doing)
            contact_tasks: list = []
            if party_tasks is not None:
                try:
                    all_tasks = party_tasks.list_by_party(party_id)
                    contact_tasks = [
                        t for t in all_tasks
                        if getattr(t, "task_kind", None) == TASK_KIND_CONTACT
                        and getattr(t, "status", None) in (TASK_STATUS_OPEN, TASK_STATUS_DOING)
                    ]
                except Exception as exc:
                    log.warning("c360 call_cockpit: contact_tasks %s: %s", party_id, exc)

            rail_primary, rail_secondary = assemble_reason_rail(
                insight=ins,
                contact_tasks=contact_tasks,
                resolved_action_ids=resolved_ids,
            )

            geo = geo_region(getattr(party, "province", None)) if party else ""

            return templates.TemplateResponse(
                "fragments/c360_call_cockpit_panel.html",
                {
                    **ctx,
                    "party": party,
                    "identities": ids,
                    "insight": ins,
                    "warning_notes": warning_notes,
                    "resolved_action_ids": resolved_ids,
                    "geo_region": geo,
                    "script": script_dict,
                    "meta": meta_dict,
                    "rail_primary": rail_primary,
                    "rail_secondary": rail_secondary,
                },
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
        claimed_tasks_ds: dict = {}
        if claimed_action_resolver is not None and ins is not None and ins.actions:
            try:
                claimed_tasks_ds = claimed_action_resolver.get_claimed_tasks_by_action_ids(
                    [a.action_id for a in ins.actions]
                )
            except Exception as exc:
                log.warning("c360: dismiss-session claimed_tasks %s: %s", party_id, exc)
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
             "claimed_tasks": claimed_tasks_ds,
             "dim_metrics": None, "snapshots": [], "timeline_available": False},
        )
