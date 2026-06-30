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
) -> None:
    """Register M08 modal (GET x2) and activity log POST route on *router*."""

    def _m08_ctx(
        request: Request,
        party_id: str,
        mode: str = "log",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
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
        }

    @router.get("/modals/m08", response_class=HTMLResponse)
    async def handle_modal_m08(
        request: Request,
        party_id: str,
        mode: str = "activity",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, note_id, party_name, task_id),
        )

    @router.get("/customers/{party_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(
        request: Request,
        party_id: str,
        mode: str = "activity",
        party_name: str = "",
        task_id: str = "",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, "", party_name, task_id),
        )

    @router.post("/customers/{party_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity(
        request: Request,
        party_id: str,
        hinh_thuc: str = Form(default="call"),
        channel_identity_id: str = Form(default=""),
        channel_value: str = Form(default=""),
        outcome: str = Form(default=""),
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
    ) -> Response:
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None
        utc_occurred = _ict_local_to_utc(occurred_at) if occurred_at.strip() else ""
        act_data: dict = {
            "party_id": party_id,
            "activity_type": _HT_TO_ACT_TYPE.get(hinh_thuc, "other"),
            "direction": "out",
            "channel": channel_value.strip() or None,
            "outcome": outcome.strip() or None,
            "body": body.strip() or None,
            "occurred_at": utc_occurred,
            "related_order_code": related_order_code.strip() or None,
            "staff_user_id": actor_id,
        }
        if outcome == "callback" and callback_at.strip():
            act_data["callback_at"] = _ict_local_to_utc(callback_at)
            act_data["create_callback_task"] = create_callback_task == "1"
        try:
            activity = activity_log.log_activity(act_data)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=400)
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("Lỗi ghi log hoạt động", status_code=500)
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
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=timeline"})
