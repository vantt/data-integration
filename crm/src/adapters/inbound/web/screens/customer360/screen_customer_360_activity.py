"""Web adapter — Customer 360 M08 modal + activity log POST routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_activity_routes().
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from domain.entities.party import partition_identities_by_channel
from domain.entities.profile import Note, PartyIdentity

from application.activity_service import ActivityFinalizeConflictError, ActivityNotFoundError
from application.activity_side_effects import execute_side_effects
from application.authorization_service import AuthorizationService

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

# Vietnamese labels for the small confirmation fragment returned to the call
# cockpit (source=call_cockpit) — covers contact_outcome values reachable from
# the outcome bar / M08 (call + messaging + visit channels).
_OUTCOME_LABELS_VI = {
    "answered": "Đã nghe", "no_answer": "Không bắt", "busy": "Bận",
    "wrong_number": "Sai số", "callback": "Hẹn lại", "refused": "Từ chối",
    "purchased": "Đã mua",
    "met": "Gặp được", "not_met": "Không gặp được",
    "replied": "Đã phản hồi", "no_reply": "Không phản hồi",
    "pending_reply": "Chờ phản hồi", "blocked": "Chặn",
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
    authz: AuthorizationService,
    task_svc=None,
    app_users=None,
    action_state=None,
    party_insights=None,
) -> None:
    """Register M08 modal (GET x2) and activity log POST route on *router*."""

    def _run_side_effects(activity, actor_id: Optional[str], **effects) -> None:
        """Closure over this router's own profile/notes/task_svc/party_insights/
        action_state — the SAME instances used everywhere else in this module —
        so legacy log-activity and the new finalize route share one executor."""
        execute_side_effects(
            activity, actor_id,
            party_id=activity.party_id,
            authz=authz,
            profile=profile, notes=notes, task_svc=task_svc,
            party_insights=party_insights, action_state=action_state,
            **effects,
        )

    def _m08_ctx(
        request: Request,
        party_id: str,
        mode: str = "log",
        note_id: str = "",
        party_name: str = "",
        task_id: str = "",
        resolve_action_ids: str = "",
        resolve_task_ids: str = "",
        prefill_body: str = "",
        activity_id: str = "",
        draft_activity_id: str = "",
        return_to: str = "redirect",
        hinh_thuc: str = "call",
    ) -> dict:
        # Normalize legacy mode names → unified 'log'.
        if mode not in ("log", "edit_note", "note_only", "edit_activity"):
            mode = "log"
        # 5a: normalize against the canonical channel keys (_HT_TO_ACT_TYPE) so the
        # modal's initial tab selection never gets pointed at an unknown value —
        # falls back to the pre-existing "call" default.
        if hinh_thuc not in _HT_TO_ACT_TYPE:
            hinh_thuc = "call"
        contact_pref_notes: list[Note] = []
        note_body = ""
        note_type_val = "general"
        note_pinned = False
        note_visibility = "team"
        party_identities: list[PartyIdentity] = []
        task_title = ""
        activity_edit = None
        if mode in ("log", "edit_activity"):
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
        # edit_activity: load the exact activity pointed to — NEVER "last log for
        # this party" (anti-pattern per report §V: rep would think they're
        # creating a new entry and silently overwrite history instead).
        if mode == "edit_activity" and activity_id.strip() and activity_log is not None:
            try:
                activity_edit = activity_log.get_activity(activity_id.strip())
            except Exception as exc:
                log.warning("m08: load edit_activity %s: %s", activity_id, exc)
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
            # S14 quick-note ("Ghi chú tạm") prefill — rendered server-side into
            # #m08-body so the value is present at swap time (see A-S14-009 JS comment).
            "prefill_body": prefill_body,
            # P1: edit_activity mode — activity_id always the exact target, never
            # inferred; activity_edit is None until it round-trips through the repo.
            "activity_id": activity_id,
            "activity_edit": activity_edit,
            # P1: set by s14StartCallSession() — mode=log form carries this back as
            # a hidden field so log-activity finalizes the draft instead of
            # inserting a fresh row (see handle_log_activity's draft_id branch).
            "draft_activity_id": draft_activity_id,
            # P0 (phase-01): threaded through to the form's hidden field so the
            # modal returns to its invoker (stay) instead of always redirecting.
            "return_to": return_to,
            # 5a: pre-selects the HÌNH THỨC tab (call/zalo/fb/email/visit/other) so
            # a worklist/cockpit Zalo or Facebook contact button opens the modal on
            # the right channel instead of always defaulting to "Cuộc gọi".
            "hinh_thuc": hinh_thuc,
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
        prefill_body: str = "",
        activity_id: str = "",
        draft_activity_id: str = "",
        return_to: str = "redirect",
        # 5a: worklist contact_btn / cockpit Zalo button pass this so the modal
        # opens pre-set to the right channel tab instead of always "Cuộc gọi".
        hinh_thuc: str = Query(default="call"),
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, note_id, party_name, task_id,
                     resolve_action_ids, resolve_task_ids, prefill_body, activity_id,
                     draft_activity_id, return_to, hinh_thuc),
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
        prefill_body: str = "",
        activity_id: str = "",
        return_to: str = "redirect",
    ) -> Response:
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            _m08_ctx(request, party_id, mode, "", party_name, task_id,
                     resolve_action_ids, resolve_task_ids, prefill_body, activity_id,
                     return_to=return_to),
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
        # P0 (activity-log disposition API): zalo-connect checkbox (M08 (d))
        zalo_connected: str = Form(default=""),
        # P0: entry-point marker — "call_cockpit" gets a small confirmation
        # fragment back (no HX-Redirect) so the outcome bar stays in place;
        # every other caller (M08 modal, timeline) keeps the redirect.
        source: str = Form(default=""),
        # P1: set by the "Gọi" identity-bar flow (POST /api/parties/{id}/call-sessions
        # ran first) — when present, this submit ADOPTS that draft (PATCH + finalize)
        # instead of inserting a fresh row, so contact_duration_s gets a real
        # started_at→finalize_at measurement. Absent for every pre-P1 caller
        # (standalone M08, quick-outcome buttons, old clients) → identical to the
        # pre-P1 fresh-insert behaviour below.
        draft_activity_id: str = Form(default=""),
        # P0 (phase-01): "stay" keeps the invoker in place (worklist row /
        # cockpit) instead of the fixed HX-Redirect below; default preserves
        # the pre-existing behaviour for every caller that doesn't send it.
        return_to: str = Form(default="redirect"),
    ) -> Response:
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None
        utc_occurred = _ict_local_to_utc(occurred_at) if occurred_at.strip() else ""
        # callback_at: check both new contact_outcome and legacy outcome for compat
        callback_at_utc = ""
        if (contact_outcome == "callback" or outcome == "callback") and callback_at.strip():
            callback_at_utc = _ict_local_to_utc(callback_at)
        # D4: persist resolve IDs in activity custom_fields snapshot (phase-02)
        bulk_action_ids = _parse_id_list(resolve_action_ids)
        bulk_task_ids = _parse_id_list(resolve_task_ids)
        _zalo_connected = zalo_connected.strip() == "1"

        draft_id = draft_activity_id.strip()
        activity = None
        already_final = False
        if draft_id:
            patch_fields: dict = {
                "contact_outcome": contact_outcome.strip() or None,
                "outcome_reason": outcome_reason.strip() or None,
                "body": body.strip() or None,
                "related_order_code": related_order_code.strip() or None,
            }
            if utc_occurred:
                patch_fields["occurred_at"] = utc_occurred
            custom_patch: dict = {}
            if bulk_task_ids:
                custom_patch["resolve_task_ids"] = bulk_task_ids
            if bulk_action_ids:
                custom_patch["resolve_action_ids"] = bulk_action_ids
            if _zalo_connected:
                custom_patch["zalo_connected"] = True
            if callback_at_utc:
                custom_patch["callback_at"] = callback_at_utc
            if custom_patch:
                patch_fields["custom_fields_patch"] = custom_patch
            try:
                activity_log.patch_activity(draft_id, patch_fields, actor_id)
                activity, already_final = activity_log.finalize_activity(draft_id)
            except ActivityNotFoundError:
                # Draft vanished/expired — fall back to the fresh-insert path below
                # rather than failing the submit outright.
                draft_id = ""
            except ActivityFinalizeConflictError as exc:
                return HTMLResponse(str(exc), status_code=409)
            except ValueError as exc:
                return HTMLResponse(str(exc), status_code=422)

        if not draft_id:
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
            if bulk_task_ids or bulk_action_ids or _zalo_connected:
                cf = act_data.get("custom_fields") or {}
                if bulk_task_ids:
                    cf["resolve_task_ids"] = bulk_task_ids
                if bulk_action_ids:
                    cf["resolve_action_ids"] = bulk_action_ids
                if _zalo_connected:
                    cf["zalo_connected"] = True
                act_data["custom_fields"] = cf
            try:
                activity = activity_log.log_activity(act_data)
            except ValueError as exc:
                return HTMLResponse(str(exc), status_code=400)
            except Exception as exc:
                log.error("log activity party %s: %s", party_id, exc)
                return HTMLResponse("Lỗi ghi log hoạt động", status_code=500)

        # "Một đường ghi duy nhất": every write side-effect (insight/auto-claim/
        # note/callback-task/followup/complete-task/bulk-resolve) runs through the
        # SAME executor the new finalize route uses — see _run_side_effects above.
        complete_task_ids = [task_id.strip()] if (complete_task == "1" and task_id.strip()) else []
        # already_final=True only happens when a draft-adopt submit double-fires
        # (e.g. accidental double-click) — skip side effects the second time so
        # note/task/insight writes are not duplicated (finalize_activity is
        # idempotent on the row itself; this mirrors that at the write-executor level).
        if not already_final:
            _run_side_effects(
                activity, actor_id,
                complete_task_ids=complete_task_ids,
                resolve_action_ids=bulk_action_ids,
                resolve_task_ids=bulk_task_ids,
                create_callback_task=(create_callback_task == "1"),
                callback_at=callback_at_utc or None,
                schedule_followup_at=schedule_followup_at.strip() or None,
                save_as_note=(
                    {"body": body, "note_type": note_type, "pinned": pinned == "1", "visibility": visibility}
                    if save_as_note == "1" and body.strip() else None
                ),
                promote_insight=(
                    {"insight_type": insight_type.strip(), "body": insight_body.strip(), "confidence": insight_confidence.strip()}
                    if promote_insight == "1" and insight_type.strip() and insight_body.strip() else None
                ),
                # Auto-claim: only when contact was logged without prior claiming and
                # staff isn't already in a structured task flow. Checks contact_outcome
                # (D2) OR legacy outcome so both paths trigger it — same guard as before.
                auto_claim=bool((contact_outcome.strip() or outcome.strip()) and not task_id.strip()),
            )
        if source.strip() == "call_cockpit":
            outcome_val = contact_outcome.strip()
            label = _OUTCOME_LABELS_VI.get(outcome_val, outcome_val or "đã ghi nhận")
            frag = (
                '<div class="s14-outcome__done">'
                f'<span class="s14-outcome__done-txt">✓ Đã ghi: {label}</span>'
                f'<button type="button" class="s14-oc-undo" '
                f'onclick="s14OpenOutcome(\'{outcome_val}\')">Hoàn tác</button>'
                '</div>'
            )
            return HTMLResponse(content=frag)
        if return_to == "stay":
            return HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"worklistRefresh": true}'})
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
        # P0 (phase-02 Amendment): the call cockpit's "+Nhắn Zalo" follow-up
        # button (s14StripZaloFollowup) fires this AFTER a call outcome was
        # already logged in the strip — without threading that outcome through,
        # this endpoint used to dismiss/complete unconditionally regardless of
        # outcome, undoing the no_answer/busy snooze execute_side_effects step 7
        # had just applied. Sourced client-side from S.chosenOutcome.
        contact_outcome: str = Form(default=""),
    ) -> Response:
        """Log an async outbound contact (Zalo/email) and resolve the given rail item.

        Endpoint: POST /customers/{party_id}/reason/resolve-async
        Form fields:
          channel         — "zalo" | "email" (required; determines activity_type)
          action_id       — optional; if set → dismiss (or snooze) via action_state
          task_id         — optional; if set → transition_status(tid, 'done')
                             (skipped/left open when contact_outcome is a
                             no-contact outcome — see resolve_actions_and_tasks)
          note            — optional free-text note logged in the activity body
          contact_outcome — optional; the outcome that triggered this follow-up
                             (e.g. "no_answer") — gates dismiss-vs-snooze the same
                             way execute_side_effects() step 7 does.

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
            # D2/AI-1: write structured contact_outcome instead of legacy free-text
            # outcome='async_sent'. channel is zalo/email → messaging group, which
            # includes 'pending_reply' (see CONTACT_OUTCOMES_BY_CHANNEL_TYPE).
            # Old rows with outcome='async_sent' are still read/rendered (read-path
            # unchanged) — no backfill.
            "contact_outcome": "pending_reply",
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
            contact_outcome=contact_outcome.strip() or None,
            party_id=party_id,
            authz=authz,
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
        script_id = form.get("script_id", "")
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
                        "script_id": script_id[:200] if script_id else "",
                        "reason_shown": reason_shown[:200] if reason_shown else "",
                    },
                }
                activity_log.log_activity(act_data)
            except Exception as exc:
                log.warning("r14_ack: activity write failed %s: %s", party_id, exc)

        return Response(status_code=204)

    # ── P1 (activity-log disposition API): draft + PATCH + finalize ──────────
    # Appended after every existing POST route so index-based test lookups
    # (router_mock.post.call_args_list[N]) for the routes above stay stable.

    @router.post("/api/parties/{party_id}/call-sessions")
    async def handle_create_call_session(
        request: Request,
        party_id: str,
        channel_identity_id: str = Form(default=""),
        task_id: str = Form(default=""),
    ) -> Response:
        """Create (or adopt) the open call draft for (staff, party) — fired when
        staff presses "Gọi" on the identity bar. Idempotent: repeat calls for the
        same (staff, party) return the same draft, never a second one.

        6a (claim-at-call-start, 260711-0838 phase 6): also claims the customer
        via `auto_claim_from_contact` unless `task_id` is present AND verified to
        already belong to this (party, actor) — closes the race window where 2
        staff can both open the same unclaimed customer before either finalizes.
        """
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None
        if not actor_id:
            return JSONResponse({"error": "unauthenticated"}, status_code=401)

        cid = channel_identity_id.strip()
        channel_val = ""
        if cid and identities is not None:
            try:
                for idn in identities.list_identities(party_id):
                    if idn.identity_id == cid:
                        channel_val = idn.identity_value
                        break
            except Exception as exc:
                log.warning("call-sessions: resolve channel_identity_id %s: %s", cid, exc)

        # 6a correction (spoofable skip-gate): task_id is a client-supplied field
        # with no inherent guarantee it belongs to this party/actor. Presence
        # alone must NOT skip auto-claim below — verify it resolves to a task
        # actually assigned to this actor for this party (e.g. S15's "Vào phiên
        # gọi" pinned it) before treating it as "already claimed". Any mismatch
        # (unknown id, wrong party, someone else's task) falls through to
        # auto-claim exactly as if task_id had been empty.
        raw_task_id = task_id.strip()
        task_already_pinned = False
        if raw_task_id and task_svc is not None:
            try:
                pinned_task = task_svc.get_task(raw_task_id)
            except Exception as exc:
                log.warning("call-sessions: get_task %s: %s", raw_task_id, exc)
                pinned_task = None
            if (
                pinned_task is not None
                and getattr(pinned_task, "party_id", None) == party_id
                and getattr(pinned_task, "assignee_user_id", None) == actor_id
            ):
                task_already_pinned = True

        try:
            activity = activity_log.create_draft(
                party_id, actor_id,
                channel_identity_id=cid or None,
                channel_value=channel_val or None,
                task_id=raw_task_id or None,
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

        resp: dict = {
            "activity_id": activity.activity_id,
            "status": activity.status,
            "started_at": activity.started_at,
            "channel_value": activity.channel,
        }

        # 6a: claim the customer now (T0→T1) rather than waiting for finalize —
        # "mở cockpit chỉ để xem KHÔNG claim" stays true, this only fires on the
        # call-session-creation POST itself. A claim failure must not block the
        # call draft that was already created above.
        if not task_already_pinned and task_svc is not None:
            try:
                display_name = party_id
                if profile is not None:
                    try:
                        p360 = profile.get_party_360(party_id)
                        display_name = p360.display_name if p360 else party_id
                    except Exception as exc:
                        log.warning("call-sessions: get_party_360 %s: %s", party_id, exc)
                claimed_task, _is_new = task_svc.auto_claim_from_contact(
                    party_id, display_name, actor_id
                )
                claimed_assignee = getattr(claimed_task, "assignee_user_id", None)
                # 6a correction (silent race loss): the unique-index-backed
                # check-then-insert isn't transactional — a true race between 2
                # staff can leave THIS request's actor as the loser with no
                # error raised. Surface it explicitly instead of proceeding as
                # if the claim succeeded for actor_id.
                if claimed_assignee and claimed_assignee != actor_id:
                    claimer_name = claimed_assignee
                    if app_users is not None:
                        try:
                            user_map = {u.user_id: u.full_name for u in app_users.list_active()}
                            claimer_name = user_map.get(claimed_assignee, claimed_assignee)
                        except Exception as exc:
                            log.warning(
                                "call-sessions: resolve claimer name %s: %s",
                                claimed_assignee, exc,
                            )
                    resp["claimed_by_other"] = claimer_name
            except Exception as exc:
                log.warning("call-sessions: auto-claim %s: %s", party_id, exc)

        return JSONResponse(resp)

    @router.patch("/api/activities/{activity_id}", response_class=HTMLResponse)
    async def handle_patch_activity(
        request: Request,
        activity_id: str,
        contact_outcome: Optional[str] = Form(default=None),
        outcome_reason: Optional[str] = Form(default=None),
        body: Optional[str] = Form(default=None),
        callback_at: Optional[str] = Form(default=None),
        related_order_code: Optional[str] = Form(default=None),
        occurred_at: Optional[str] = Form(default=None),
        channel_identity_id: Optional[str] = Form(default=None),
        zalo_connected: Optional[str] = Form(default=None),
        # "1" when submitted from M08 edit_activity mode — triggers the audit
        # trail (edited_at/edited_by/previous_outcome) + redirects back to
        # timeline instead of returning 204 (matches every other M08 submit).
        edit_mode: str = Form(default=""),
        # P0 (phase-01 amendment): edit_activity callers opened with
        # return_to=stay (e.g. cockpit's "⋯ Chi tiết") must NOT be redirected
        # away — default "redirect" keeps the pre-existing edit_mode behaviour.
        return_to: str = Form(default="redirect"),
    ) -> Response:
        """Autosave a subset of fields onto a draft (or edit an existing activity
        via M08 edit_activity mode). No side effects — see finalize for those."""
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None

        fields: dict = {}
        if contact_outcome is not None:
            fields["contact_outcome"] = contact_outcome.strip() or None
        if outcome_reason is not None:
            fields["outcome_reason"] = outcome_reason.strip() or None
        if body is not None:
            fields["body"] = body.strip() or None
        if related_order_code is not None:
            fields["related_order_code"] = related_order_code.strip() or None
        if occurred_at is not None and occurred_at.strip():
            fields["occurred_at"] = _ict_local_to_utc(occurred_at)

        custom_patch: dict = {}
        if callback_at is not None and callback_at.strip():
            custom_patch["callback_at"] = _ict_local_to_utc(callback_at)
        if channel_identity_id is not None:
            custom_patch["channel_identity_id"] = channel_identity_id.strip() or None
        if zalo_connected is not None:
            custom_patch["zalo_connected"] = zalo_connected.strip() == "1"
        if custom_patch:
            fields["custom_fields_patch"] = custom_patch

        try:
            activity = activity_log.patch_activity(
                activity_id, fields, actor_id, is_edit_mode=(edit_mode == "1"),
            )
        except ActivityNotFoundError:
            return HTMLResponse("Không tìm thấy hoạt động", status_code=404)
        except ValueError as exc:
            return HTMLResponse(str(exc), status_code=422)

        if edit_mode == "1":
            if return_to == "stay":
                return HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"activitySaved": true}'})
            return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{activity.party_id}?tab=timeline"})
        return Response(status_code=204)

    @router.post("/api/activities/{activity_id}/finalize", response_class=HTMLResponse)
    async def handle_finalize_activity(
        request: Request,
        activity_id: str,
        complete_task_ids: str = Form(default=""),
        resolve_action_ids: str = Form(default=""),
        resolve_task_ids: str = Form(default=""),
        create_callback_task: str = Form(default=""),
        schedule_followup_at: str = Form(default=""),
        save_as_note: str = Form(default=""),
        note_type: str = Form(default="outcome"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
        promote_insight: str = Form(default="0"),
        insight_type: str = Form(default=""),
        insight_body: str = Form(default=""),
        insight_confidence: str = Form(default=""),
        contact_duration_s: str = Form(default=""),
    ) -> Response:
        """Finalize a draft — 409 if it has no contact_outcome yet, idempotent
        otherwise. Runs every side effect through the same executor as the
        legacy log-activity route. Returns a small "✓ đã chốt" fragment — never
        a redirect (decision: cockpit stays put after finalize)."""
        current_user = getattr(request.state, "current_user", None)
        actor_id: Optional[str] = current_user.user_id if current_user else None

        try:
            duration_override = int(contact_duration_s) if contact_duration_s.strip() else None
        except ValueError:
            duration_override = None

        try:
            activity, already_final = activity_log.finalize_activity(
                activity_id, contact_duration_s_override=duration_override,
            )
        except ActivityNotFoundError:
            return HTMLResponse("Không tìm thấy hoạt động", status_code=404)
        except ActivityFinalizeConflictError as exc:
            return HTMLResponse(str(exc), status_code=409)

        if not already_final:
            callback_at_val = None
            if activity.custom_fields:
                callback_at_val = activity.custom_fields.get("callback_at")
            _run_side_effects(
                activity, actor_id,
                complete_task_ids=_parse_id_list(complete_task_ids),
                resolve_action_ids=_parse_id_list(resolve_action_ids),
                resolve_task_ids=_parse_id_list(resolve_task_ids),
                create_callback_task=(create_callback_task == "1"),
                callback_at=callback_at_val,
                schedule_followup_at=schedule_followup_at.strip() or None,
                save_as_note=(
                    {"body": activity.body, "note_type": note_type, "pinned": pinned == "1", "visibility": visibility}
                    if save_as_note == "1" and (activity.body or "").strip() else None
                ),
                promote_insight=(
                    {"insight_type": insight_type.strip(), "body": insight_body.strip(), "confidence": insight_confidence.strip()}
                    if promote_insight == "1" and insight_type.strip() and insight_body.strip() else None
                ),
                auto_claim=bool(activity.contact_outcome and not activity.task_id),
            )

        label = _OUTCOME_LABELS_VI.get(activity.contact_outcome or "", activity.contact_outcome or "đã ghi nhận")
        frag = (
            '<div class="s14-outcome__done">'
            f'<span class="s14-outcome__done-txt">✓ Đã chốt: {label}</span>'
            '</div>'
        )
        return HTMLResponse(content=frag)
