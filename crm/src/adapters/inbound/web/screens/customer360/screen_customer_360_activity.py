"""Web adapter — Customer 360 M08 modal + activity log POST routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_activity_routes().
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.party import partition_identities_by_channel
from domain.entities.profile import Note, PartyIdentity

from adapters.inbound.web.screens.customer360.outcome_resolve_helpers import (
    parse_id_list as _parse_id_list,
    bulk_resolve as _bulk_resolve,
)

log = logging.getLogger(__name__)

_ICT = timezone(timedelta(hours=7))

_HT_TO_ACT_TYPE = {
    "call": "call", "zalo": "chat", "fb": "chat",
    "email": "email", "visit": "visit", "other": "other",
}


def _ict_local_to_utc(ict_str: str) -> str:
    """Parse datetime-local input (assumed ICT/UTC+7) → UTC ISO-8601 string."""
    try:
        dt = datetime.strptime(ict_str.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=_ICT)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ""


def register_activity_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    profile,
    identities,
    notes,
    activity_log,
    task_svc=None,
    app_users=None,
    action_state=None,
) -> None:
    """Register M08 modal (GET x2) and activity log POST route on *router*."""

    def _m08_ctx(
        request: Request,
        party_id: str,
        mode: str = "log",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
        resolve_action_ids: str = "",
        resolve_task_ids: str = "",
    ) -> dict:
        # Normalize legacy mode names → unified 'log'.
        if mode not in ("log", "edit_note", "note_only"):
            mode = "log"
        contact_pref_notes: list[Note] = []
        note_body = ""
        note_type_val = "general"
        note_pinned = False
        note_visibility = "team"
        party_identities: list[PartyIdentity] = []
        task_title = ""
        if mode == "log":
            try:
                contact_pref_notes = [
                    n for n in notes.list_notes(party_id)
                    if not n.deleted_at and n.note_type == "contact_pref" and n.pinned
                ]
            except Exception as exc:
                log.warning("m08: contact_pref_notes %s: %s", party_id, exc)
            try:
                party_identities = identities.list_identities(party_id)
            except Exception as exc:
                log.warning("m08: identities %s: %s", party_id, exc)
            if task_id.strip() and task_svc is not None:
                try:
                    t = task_svc.get_task(task_id.strip())
                    if t is not None:
                        task_title = getattr(t, "title", "")
                except Exception as exc:
                    log.warning("m08: get_task %s: %s", task_id, exc)
        channel_groups = partition_identities_by_channel(party_identities)
        if mode == "edit_note" and note_id:
            try:
                existing = next(
                    (n for n in notes.list_notes(party_id) if n.note_id == note_id), None
                )
                if existing:
                    note_body = existing.body
                    note_type_val = existing.note_type
                    note_pinned = existing.pinned
                    note_visibility = existing.visibility
            except Exception as exc:
                log.warning("m08: load edit_note %s: %s", note_id, exc)
        return {
            "request": request,
            "party_id": party_id,
            "mode": mode,
            "note_id": note_id,
            "party_name": party_name,
            "task_id": task_id,
            "task_title": task_title,
            "identities": party_identities,
            "call_ids":   channel_groups["call"],
            "zalo_ids":   channel_groups["zalo"],
            "fb_ids":     channel_groups["fb"],
            "email_ids":  channel_groups["email"],
            "contact_pref_notes": contact_pref_notes,
            "note_body": note_body,
            "note_type_val": note_type_val,
            "note_pinned": note_pinned,
            "note_visibility": note_visibility,
            "resolve_action_ids": resolve_action_ids,
            "resolve_task_ids": resolve_task_ids,
        }

    @router.get("/modals/m08", response_class=HTMLResponse)
    async def handle_modal_m08(
        request: Request,
        party_id: str,
        mode: str = "activity",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
        resolve_action_ids: str = "",
        resolve_task_ids: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, note_id, party_name, task_id,
                     resolve_action_ids, resolve_task_ids),
        )

    @router.get("/customers/{party_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(
        request: Request,
        party_id: str,
        mode: str = "activity",
        party_name: str = "",
        task_id: str = "",
        resolve_action_ids: str = "",
        resolve_task_ids: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, "", party_name, task_id,
                     resolve_action_ids, resolve_task_ids),
        )

    @router.post("/customers/{party_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity(
        request: Request,
        party_id: str,
        hinh_thuc: str = Form(default="call"),
        channel_identity_id: str = Form(default=""),
        channel_value: str = Form(default=""),
        outcome: str = Form(default=""),          # legacy field; kept for backward compat + auto-claim guard
        contact_outcome: str = Form(default=""),  # D2 structured enum per channel_type
        outcome_reason: str = Form(default=""),   # D2 nullable; required when contact_outcome='refused'
        body: str = Form(default=""),
        occurred_at: str = Form(default=""),
        related_order_code: str = Form(default=""),
        callback_at: str = Form(default=""),
        create_callback_task: str = Form(default=""),
        save_as_note: str = Form(default=""),
        note_type: str = Form(default="outcome"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
        schedule_followup_at: str = Form(default=""),
        task_id: str = Form(default=""),
        complete_task: str = Form(default=""),
        resolve_action_ids: str = Form(default=""),
        resolve_task_ids: str = Form(default=""),
        # Item 2 (Phase 06): promote insight from activity log
        promote_insight: str = Form(default="0"),
        insight_type: str = Form(default=""),
        insight_body: str = Form(default=""),
        insight_confidence: str = Form(default=""),
    ) -> Response:
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None
        utc_occurred = _ict_local_to_utc(occurred_at) if occurred_at.strip() else ""
        act_data: dict = {
            "party_id": party_id,
            "activity_type": _HT_TO_ACT_TYPE.get(hinh_thuc, "other"),
            "direction": "out",
            "channel": channel_value.strip() or None,
            "channel_type": hinh_thuc.strip() or None,
            # D2 Phase 03: contact_outcome replaces outcome for new rows.
            # Legacy outcome kept in act_data only when contact_outcome absent (backward compat).
            "contact_outcome": contact_outcome.strip() or None,
            "outcome_reason": outcome_reason.strip() or None,
            "body": body.strip() or None,
            "occurred_at": utc_occurred,
            "related_order_code": related_order_code.strip() or None,
            "staff_user_id": actor_id,
            "task_id": task_id.strip() or None,
        }
        # callback_at: check both new contact_outcome and legacy outcome for compat
        if (contact_outcome == "callback" or outcome == "callback") and callback_at.strip():
            act_data["callback_at"] = _ict_local_to_utc(callback_at)
            act_data["create_callback_task"] = create_callback_task == "1"
        # D4: persist resolve IDs in activity custom_fields snapshot (phase-02)
        _bulk_action_preview = _parse_id_list(resolve_action_ids)
        _bulk_task_preview = _parse_id_list(resolve_task_ids)
        if _bulk_action_preview or _bulk_task_preview:
            cf = act_data.get("custom_fields") or {}
            if _bulk_task_preview:
                cf["resolve_task_ids"] = _bulk_task_preview
            if _bulk_action_preview:
                cf["resolve_action_ids"] = _bulk_action_preview
            act_data["custom_fields"] = cf
        try:
            activity = activity_log.log_activity(act_data)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("Lỗi ghi log hoạt động", status_code=500)
        # Item 2 (Phase 06): promote insight — party_insights not wired into this route;
        # log warning and skip silently per spec constraint.
        if promote_insight == "1" and insight_type.strip() and insight_body.strip():
            log.warning(
                "promote_insight requested for party %s (type=%s) but party_insights "
                "service not in scope for register_activity_routes — skipped",
                party_id, insight_type.strip(),
            )
        # Auto-claim: create a claim task when contact is logged without prior claiming.
        # Skip when task_id is present — staff is already in the structured task flow.
        # Check contact_outcome (D2) OR legacy outcome field so both paths trigger claim.
        if (contact_outcome.strip() or outcome.strip()) and actor_id and task_svc is not None and not task_id.strip():
            try:
                party360 = profile.get_party_360(party_id)
                customer_name = party360.display_name if party360 else ""
                task_svc.auto_claim_from_contact(party_id, customer_name, actor_id)
            except Exception as exc:
                log.warning("m08: auto-claim %s: %s", party_id, exc)
        if save_as_note == "1" and body.strip():
            try:
                notes.add_note(
                    party_id, body.strip(),
                    author_user_id=actor_id,
                    note_type=note_type or "outcome",
                    pinned=pinned == "1",
                    visibility=visibility or "team",
                    source_activity_id=getattr(activity, "activity_id", None),
                )
            except Exception as exc:
                log.warning("m08: linked note %s: %s", party_id, exc)
        if task_svc is not None and schedule_followup_at.strip():
            try:
                party360 = profile.get_party_360(party_id)
                name = party360.display_name if party360 else party_id
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Theo dõi: {name}",
                    "due_at": schedule_followup_at.strip(),
                    "source": "manual",
                    "priority": 0,
                })
            except Exception as exc:
                log.warning("m08: schedule followup task %s: %s", party_id, exc)
        if complete_task == "1" and task_id.strip() and task_svc is not None:
            try:
                task_svc.transition_status(task_id.strip(), "done")
            except Exception as exc:
                log.warning("m08: complete_task %s: %s", task_id, exc)
        # Outcome bulk-resolve: dismiss action_ids + complete task_ids from cockpit outcome bar.
        # skip_task_id prevents double-resolution when the same task_id already completed above.
        bulk_action_ids = _parse_id_list(resolve_action_ids)
        bulk_task_ids = _parse_id_list(resolve_task_ids)
        if bulk_action_ids or bulk_task_ids:
            _bulk_resolve(
                action_ids=bulk_action_ids,
                task_ids=bulk_task_ids,
                action_state=action_state,
                task_svc=task_svc,
                skip_task_id=task_id.strip() if complete_task == "1" else "",
                actor_id=actor_id or "",
            )
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=timeline"})

    # ── A-S14-026: Async-resolve (Zalo / email without a call) ───────────────

    @router.post("/customers/{party_id}/reason/resolve-async", response_class=HTMLResponse)
    async def handle_resolve_async(
        request: Request,
        party_id: str,
        channel: str = Form(default=""),
        action_id: str = Form(default=""),
        task_id: str = Form(default=""),
        note: str = Form(default=""),
    ) -> Response:
        """Log an async outbound contact (Zalo/email) and resolve the given rail item.

        Endpoint: POST /customers/{party_id}/reason/resolve-async
        Form fields:
          channel   — "zalo" | "email" (required; determines activity_type)
          action_id — optional; if set → dismiss via action_state
          task_id   — optional; if set → transition_status(tid, 'done')
          note      — optional free-text note logged in the activity body

        Returns 204 (no content) — HTMX should target the specific rail item and
        swap it out; the cockpit panel is NOT re-rendered to preserve call state.
        """
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None

        ch = channel.strip().lower()
        _CH_TO_TYPE = {"zalo": "chat", "email": "email"}
        act_type = _CH_TO_TYPE.get(ch, "other")

        act_data: dict = {
            "party_id": party_id,
            "activity_type": act_type,
            "direction": "out",
            "channel": ch or None,
            "channel_type": ch or None,
            "outcome": "async_sent",
            "body": note.strip() or None,
            "staff_user_id": actor_id,
            "task_id": task_id.strip() or None,
        }
        try:
            activity_log.log_activity(act_data)
        except Exception as exc:
            log.error("resolve_async: log activity %s: %s", party_id, exc)
            return HTMLResponse("Lỗi ghi log", status_code=500)

        _bulk_resolve(
            action_ids=_parse_id_list(action_id),
            task_ids=_parse_id_list(task_id),
            action_state=action_state,
            task_svc=task_svc,
            actor_id=actor_id or "",
        )

        return Response(status_code=204)

    # ── A-S14-027: R14 warn-with-ack audit log ───────────────────────────────

    @router.post("/customers/{party_id}/r14-ack", response_class=HTMLResponse)
    async def handle_r14_ack(request: Request, party_id: str) -> Response:
        """Log R14 override acknowledgment. Returns 204 — no panel re-render (Invariant §9).

        The frontend performs a pure-JS unlock (hide banner + remove s14-locked class).
        This endpoint only writes an audit activity so the override is traceable.
        """
        form = await request.form()
        reason_shown = form.get("reason_shown", "")
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None

        if activity_log is not None:
            try:
                act_data: dict = {
                    "party_id": party_id,
                    "activity_type": "other",
                    "direction": "internal",
                    "subject": "R14 override: NV đã xác minh và tiếp tục gọi theo kịch bản",
                    "body": None,
                    "staff_user_id": actor_id,
                    "custom_fields": {
                        "r14_ack": True,
                        "reason_shown": reason_shown[:200] if reason_shown else "",
                    },
                }
                activity_log.log_activity(act_data)
            except Exception as exc:
                log.warning("r14_ack: activity write failed %s: %s", party_id, exc)

        return Response(status_code=204)
