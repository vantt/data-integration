"""Shared side-effect executor for activity finalization.

Both the legacy `POST /customers/{id}/log-activity` handler (M08 standalone +
the 3 quick-outcome cockpit buttons) and the new
`POST /api/activities/{id}/finalize` route call `execute_side_effects()` right
after an activity's contact_outcome is committed — this is the "một đường ghi
duy nhất" invariant: exactly one function walks note/insight/task/bulk-resolve
writes, so a change to one side effect can't silently diverge between the two
entry points (see the `party_insights` factory lesson: UI wired to a route
without the write actually happening downstream, from the outreach-effort
report referenced by this phase's plan).

Pure orchestration — ports are duck-typed (may be None → step skipped), no
FastAPI import, no adapter imports (mirrors application/activity_service.py's
"pure domain + ports only" convention). Callable from any adapter.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from domain.entities.profile import PartyInsight

log = logging.getLogger(__name__)

# Quyết định UX 2026-07-11 (①): outcome cho thấy cuộc gọi KHÔNG thành công (khách
# không nhấc máy / đang bận) không nên "resolve" tín hiệu như một cuộc gọi thành
# công — snooze ngắn hạn để action quay lại hàng đợi thay vì dismiss TTL 30 ngày
# (mất tín hiệu thật). Shared by execute_side_effects() step 7 below AND
# outcome_resolve_helpers.bulk_resolve() (the /reason/resolve-async "+Nhắn Zalo"
# follow-up path) so both resolve entry points apply the same gate — see the
# phase-02 Amendment: without this, that second path silently undid the snooze.
_NO_CONTACT_OUTCOMES = frozenset({"no_answer", "busy"})
_NO_CONTACT_SNOOZE_DAYS = 2


def parse_id_list(raw: str) -> list[str]:
    """Split a comma-separated id string into non-empty stripped ids."""
    return [s.strip() for s in raw.split(",") if s.strip()]


def resolve_actions_and_tasks(
    action_ids: list[str],
    task_ids: list[str],
    action_state,
    task_svc,
    contact_outcome: Optional[str],
    actor_id: Optional[str] = None,
) -> None:
    """Outcome-aware bulk resolve — dismiss+done normally, snooze+leave-open for
    `_NO_CONTACT_OUTCOMES`. Shared by execute_side_effects() step 7 and
    outcome_resolve_helpers.bulk_resolve() so the gate can't be bypassed by
    routing through the other resolve entry point (phase-02 Amendment).

    contact_outcome ∈ {"no_answer", "busy"} → snooze `action_ids` via
    `action_state.snooze()`, `_NO_CONTACT_SNOOZE_DAYS` days out. `task_ids` are
    left untouched (claimed ownership should survive a failed contact attempt).

    Any other outcome (including None/empty) → prior behavior: dismiss
    `action_ids` (TTL 30d) and transition `task_ids` to "done".

    Never raises — each item is independently try/except-logged.
    """
    uid: Optional[str] = actor_id or None
    outcome = contact_outcome or ""
    if outcome in _NO_CONTACT_OUTCOMES:
        until_date = (
            datetime.now(timezone.utc) + timedelta(days=_NO_CONTACT_SNOOZE_DAYS)
        ).strftime("%Y-%m-%d")
        if action_state is not None:
            for aid in action_ids:
                try:
                    action_state.snooze(aid, until_date, user_id=uid)
                except Exception as exc:
                    log.warning("resolve: snooze action %s: %s", aid, exc)
    else:
        if action_state is not None:
            for aid in action_ids:
                try:
                    action_state.dismiss(aid, user_id=uid)
                except Exception as exc:
                    log.warning("resolve: dismiss action %s: %s", aid, exc)
        if task_svc is not None:
            for tid in task_ids:
                try:
                    task_svc.transition_status(tid, "done")
                except Exception as exc:
                    log.warning("resolve: transition task %s: %s", tid, exc)


def execute_side_effects(
    activity,
    actor_id: Optional[str],
    *,
    party_id: str,
    profile=None,
    notes=None,
    task_svc=None,
    party_insights=None,
    action_state=None,
    complete_task_ids: Optional[list[str]] = None,
    resolve_action_ids: Optional[list[str]] = None,
    resolve_task_ids: Optional[list[str]] = None,
    create_callback_task: bool = False,
    callback_at: Optional[str] = None,
    schedule_followup_at: Optional[str] = None,
    save_as_note: Optional[dict] = None,
    promote_insight: Optional[dict] = None,
    auto_claim: bool = False,
) -> None:
    """Run every write side-effect of a finalized activity.

    Never raises — each step is independently try/except-logged, matching the
    legacy handler's per-step failure isolation (one bad side effect must not
    roll back the activity that was already committed).

    Parameters mirror the finalize payload from the phase-02 API spec:
    complete_task_ids/resolve_action_ids/resolve_task_ids/create_callback_task/
    schedule_followup_at/save_as_note/promote_insight, plus `auto_claim` (moved
    here from the old POST handler per decision — never claim just for opening
    the cockpit/creating a draft).
    """
    complete_task_ids = complete_task_ids or []
    resolve_action_ids = resolve_action_ids or []
    resolve_task_ids = resolve_task_ids or []

    def _display_name() -> str:
        if profile is None:
            return party_id
        try:
            p360 = profile.get_party_360(party_id)
            return p360.display_name if p360 else party_id
        except Exception as exc:
            log.warning("side_effects: get_party_360 %s: %s", party_id, exc)
            return party_id

    # 1. Promote insight
    if promote_insight and promote_insight.get("insight_type") and (promote_insight.get("body") or "").strip():
        if party_insights is not None:
            try:
                party_insights.add_insight(PartyInsight(
                    insight_id=str(uuid.uuid4()),
                    party_id=party_id,
                    insight_type=promote_insight["insight_type"],
                    body=promote_insight["body"].strip(),
                    confidence=promote_insight.get("confidence") or "medium",
                    created_by=actor_id,
                    source_note_id=None,
                    created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                ))
            except Exception as exc:
                log.warning("side_effects: promote_insight %s: %s", party_id, exc)
        else:
            log.warning(
                "side_effects: promote_insight requested for %s (type=%s) but party_insights not wired",
                party_id, promote_insight.get("insight_type"),
            )

    # 2. Auto-claim — only when no task_id is already driving this contact (staff
    # already in the structured task flow) and there IS a contact_outcome.
    #
    # 6a (260711-0838 phase 6, "duplicate auto-claim path" correction): since
    # claim-at-call-start shipped, `POST /api/parties/{id}/call-sessions`
    # (handle_create_call_session) now ALSO calls auto_claim_from_contact at
    # T0→T1, before this finalize-time call ever runs. For the common path
    # (staff pressed "Gọi" first) this step is a safety-net no-op —
    # auto_claim_from_contact's own get_customer_claim early-return makes the
    # second call idempotent, so calling it twice per activity is harmless, not
    # a bug. It's kept here (not removed) for callers that reach
    # execute_side_effects without ever going through call-session creation —
    # e.g. a standalone M08 log with no prior "Gọi" press.
    if auto_claim and actor_id and task_svc is not None:
        try:
            task_svc.auto_claim_from_contact(party_id, _display_name(), actor_id)
        except Exception as exc:
            log.warning("side_effects: auto-claim %s: %s", party_id, exc)

    # 3. Save as note (reuses the activity's own body — same text, separate surface)
    if save_as_note and (save_as_note.get("body") or "").strip():
        if notes is not None:
            try:
                notes.add_note(
                    party_id, save_as_note["body"].strip(),
                    author_user_id=actor_id,
                    note_type=save_as_note.get("note_type") or "outcome",
                    pinned=bool(save_as_note.get("pinned")),
                    visibility=save_as_note.get("visibility") or "team",
                    source_activity_id=getattr(activity, "activity_id", None),
                )
            except Exception as exc:
                log.warning("side_effects: save_as_note %s: %s", party_id, exc)

    # 4. Callback task — contact_outcome='callback' + a callback_at + the "tạo task
    # nhắc" flag. NOTE: this was dead code in the pre-P1 handler (callback_at/
    # create_callback_task were captured into act_data but nothing ever read them
    # back out to create a task) — fixed here as part of unifying the executor.
    if create_callback_task and callback_at:
        if task_svc is not None:
            try:
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Gọi lại: {_display_name()}",
                    "due_at": callback_at,
                    "source": "manual",
                    "priority": 0,
                    "assignee_user_id": actor_id,
                    "created_by": actor_id,
                })
            except Exception as exc:
                log.warning("side_effects: create_callback_task %s: %s", party_id, exc)

    # 5. Follow-up task
    if schedule_followup_at:
        if task_svc is not None:
            try:
                task_svc.create_task({
                    "party_id": party_id,
                    "title": f"Theo dõi: {_display_name()}",
                    "due_at": schedule_followup_at,
                    "source": "manual",
                    "priority": 0,
                    "assignee_user_id": actor_id,
                    "created_by": actor_id,
                })
            except Exception as exc:
                log.warning("side_effects: schedule_followup %s: %s", party_id, exc)

    # 6. Complete linked task(s)
    if complete_task_ids and task_svc is not None:
        for tid in complete_task_ids:
            try:
                task_svc.transition_status(tid, "done")
            except Exception as exc:
                log.warning("side_effects: complete_task %s: %s", tid, exc)

    # 7. Bulk-resolve (dismiss actions + complete tasks) from the cockpit outcome
    # bar's rail — skip any task_id already handled by step 6 above so a task
    # showing up in both complete_task_ids and resolve_task_ids is not
    # transitioned twice. Outcome-aware (①): no_answer/busy snoozes instead of
    # dismissing and leaves remaining_task_ids open — see resolve_actions_and_tasks.
    skip_ids = set(complete_task_ids)
    remaining_task_ids = [t for t in resolve_task_ids if t not in skip_ids]
    if resolve_action_ids or remaining_task_ids:
        resolve_actions_and_tasks(
            resolve_action_ids, remaining_task_ids, action_state, task_svc,
            getattr(activity, "contact_outcome", None), actor_id,
        )
