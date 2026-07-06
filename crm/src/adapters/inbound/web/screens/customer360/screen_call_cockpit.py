"""Web adapter — S14 full-screen Call Cockpit route.

GET /customers/{party_id}/call  — full-screen shell embedding the cockpit fragment.
    Optional ?task_id= pins that task's reason as PRIMARY and switches the
    return chrome from "Khách kế →" to "Quay lại task".

This module is registered by make_customer_360_router() via
register_call_cockpit_route() — not as a standalone factory.  It receives
closed-over helpers (_load_base, _load_insight, _sapo_customer_id) and repos
from the parent factory to avoid duplicating wiring.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from application.geography import geo_region
from application.reason_rail import assemble_reason_rail
from domain.entities.task import TASK_KIND_CONTACT, TASK_STATUS_OPEN, TASK_STATUS_DOING

log = logging.getLogger(__name__)


def register_call_cockpit_route(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    _load_base,           # closure from make_customer_360_router
    _load_insight,        # closure from make_customer_360_router
    _sapo_customer_id,    # closure from make_customer_360_router
    notes=None,
    party_tasks=None,
    approach_repo=None,
    action_task_resolver=None,
) -> None:
    """Register GET /customers/{party_id}/call on *router*."""

    @router.get("/customers/{party_id}/call", response_class=HTMLResponse)
    async def handle_call_cockpit_fullscreen(
        request: Request,
        party_id: str,
        task_id: str = "",
        queue_ids: str = "",
        queue_pos: int = 0,
    ) -> Response:
        """Full-screen call cockpit shell.

        Context contract:
          party, identities, insight, warning_notes, resolved_action_ids,
          geo_region, script, meta, rail_primary, rail_secondary,
          pinned_task_id, return_target
        """
        party, ids = _load_base(party_id)
        if party is None:
            return HTMLResponse("Không tìm thấy khách hàng", status_code=404)

        customer_id = _sapo_customer_id(ids)
        ins = _load_insight(ids)

        # Warning notes (type=warning)
        warning_notes: list = []
        if notes is not None:
            try:
                all_notes = notes.list_notes(party_id)
                warning_notes = [
                    n for n in all_notes
                    if not n.deleted_at and n.note_type == "warning"
                ]
            except Exception as exc:
                log.warning("call_cockpit: warning_notes %s: %s", party_id, exc)

        # Resolved action_ids
        resolved_ids: set = set()
        if action_task_resolver is not None:
            try:
                resolved_ids = action_task_resolver.resolved_action_ids(party_id)
            except Exception as exc:
                log.warning("call_cockpit: resolved_action_ids %s: %s", party_id, exc)

        # Approach script (cache-first per §2 of S14-implementation-notes)
        script_dict = None
        meta_dict = None
        if customer_id and approach_repo is not None:
            try:
                scr = approach_repo.get_by_customer_id(customer_id)
                if scr is not None and isinstance(scr.data, dict) and "approach" in scr.data:
                    script_dict = scr.data
                    meta_dict = {
                        "recommended": scr.recommended,
                        "confidence": scr.confidence,
                        "refreshed_at": scr.refreshed_at,
                        "template_version": scr.template_version,
                    }
            except Exception as exc:
                log.warning("call_cockpit: approach script %s: %s", party_id, exc)

        # Contact tasks (open + doing) for reason rail
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
                log.warning("call_cockpit: contact_tasks %s: %s", party_id, exc)

        # Reason rail assembly
        pinned_task_id = task_id.strip() or None
        rail_primary, rail_secondary = assemble_reason_rail(
            insight=ins,
            contact_tasks=contact_tasks,
            resolved_action_ids=resolved_ids,
            pinned_task_id=pinned_task_id,
        )

        # Item 1 (Phase 06): parse party.custom into a dict for collect row gating
        party_custom: dict = {}
        if party is not None:
            raw_custom = getattr(party, "custom", None)
            if raw_custom:
                try:
                    party_custom = (
                        json.loads(raw_custom) if isinstance(raw_custom, str)
                        else (raw_custom if isinstance(raw_custom, dict) else {})
                    )
                except Exception:
                    party_custom = {}

        # Return target changes when entering from a task (S15 "Vào phiên gọi")
        return_target = f"/tasks/{pinned_task_id}" if pinned_task_id else None

        # A2: call-mode queue navigation
        queue_list = [q.strip() for q in queue_ids.split(",") if q.strip()] if queue_ids else []
        queue_total = len(queue_list)
        # Auto-correct queue_pos to this customer's actual position in the list
        if party_id in queue_list:
            queue_pos = queue_list.index(party_id)
        queue_next_party_id = queue_list[queue_pos + 1] if queue_pos + 1 < queue_total else None

        return templates.TemplateResponse(
            "call_cockpit.html",
            {
                "request": request,
                "party_id": party_id,
                "party": party,
                "identities": ids,
                "insight": ins,
                "warning_notes": warning_notes,
                "resolved_action_ids": resolved_ids,
                "geo_region": geo_region(getattr(party, "province", None)),
                "script": script_dict,
                "meta": meta_dict,
                "rail_primary": rail_primary,
                "rail_secondary": rail_secondary,
                "pinned_task_id": pinned_task_id,
                "return_target": return_target,
                # A2: queue context
                "queue_ids": queue_ids,
                "queue_total": queue_total,
                "queue_pos": queue_pos,
                "queue_next_party_id": queue_next_party_id,
                # Item 1 (Phase 06): custom fields for collect row gating
                "party_custom": party_custom,
            },
        )
