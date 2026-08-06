"""Web adapter — Customer 360 HTMX panel fragment routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_panel_routes().
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from application.geography import geo_region
from application.health_domain_collect import load_health_domain_collect_context
from application.reason_rail import assemble_reason_rail
from domain.entities.cache_insight import CustomerDimMetrics
from domain.entities.profile import PartyIdentity, PartyInsight
from domain.entities.task import (
    TASK_KIND_CONTACT, TASK_STATUS_OPEN, TASK_STATUS_DOING, VALID_UNCLAIM_REASONS,
)
from adapters.inbound.web.screens.customer360.screen_call_cockpit import (
    build_draft_activity_ctx,
)

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
    tags=None,           # Phase 02 (260706-0833): health_domain gap detection
    activity_log=None,   # Phase 03 (disposition strip v2): draft recovery on reload
    render_suggestion_settings_panel=None,  # P07: callable(request, party_id) -> Response
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
        request: Request, party_id: str, reason: str = Form(default="")
    ) -> Response:
        """Cancel the per-customer claim task from C360.

        Same ownership/reason rules as the worklist unclaim route (S01): 401
        unauthenticated, 422 missing/invalid reason, 403 non-assignee — logic
        itself lives once in TaskService.unclaim_customer_actions.
        """
        uid = getattr(getattr(request.state, "current_user", None), "user_id", "")
        if not uid:
            return HTMLResponse("", status_code=401)
        if reason not in VALID_UNCLAIM_REASONS:
            return HTMLResponse("", status_code=422)

        if task_svc is None:
            return await _render_insight_panel_response(request, party_id)

        try:
            result = task_svc.unclaim_customer_actions(party_id, actor_id=uid, reason=reason)
        except Exception as exc:
            log.error("c360: unclaim customer %s: %s", party_id, exc)
            return HTMLResponse("", status_code=500)

        if result == "forbidden":
            return HTMLResponse("", status_code=403)

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

            # Item 2 (Phase 02, 260706-0833): health_domain gap detection for collect row 1
            health_ctx = load_health_domain_collect_context(tags, party_id)

            # Phase 03 (disposition strip v2): mid-call reload recovery — same
            # helper the full-screen host uses, so both hosts agree on state.
            current_user = getattr(request.state, "current_user", None)
            draft_activity = build_draft_activity_ctx(activity_log, current_user, party_id)

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
                    "draft_activity": draft_activity,
                    **health_ctx,
                },
            )
        if panel == "suggestion_settings":
            if render_suggestion_settings_panel is None:
                return HTMLResponse("panel not found", status_code=404)
            return await render_suggestion_settings_panel(request, party_id)
        return HTMLResponse("panel not found", status_code=404)

    # NOTE (6b, 260711-0838 phase 6): the bulk-dismiss route that used to live
    # here (`POST /customers/{party_id}/actions/dismiss-session`,
    # `handle_dismiss_session`) was removed — it called `action_state.dismiss()`
    # directly with no activity/note write, bypassing the "một đường ghi duy
    # nhất" invariant every other resolve path goes through. The "Hoàn tất ✓"
    # button (`c360_insight_panel.html`) now opens M08 with `resolve_action_ids`
    # built from the currently-checked boxes, routing the same batch resolve
    # through `execute_side_effects` instead. Confirmed caller-safe before
    # removal: grep found zero test coverage and zero other callers of this
    # route (only the one template link, which was updated in the same change).
