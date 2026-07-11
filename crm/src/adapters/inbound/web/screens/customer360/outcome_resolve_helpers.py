"""outcome_resolve_helpers.py — pure-logic helpers for Phase-04 outcome bulk-resolve.

No FastAPI / web dependency — imported by both the activity routes module and the
pure-logic unit tests (which run outside Docker where fastapi is absent).
"""
from __future__ import annotations

import logging
from typing import Optional

from application.activity_side_effects import resolve_actions_and_tasks
from application.authorization_service import AuthorizationService

log = logging.getLogger(__name__)


def parse_id_list(raw: str) -> list[str]:
    """Split a comma-separated id string into a list of non-empty stripped ids."""
    return [s.strip() for s in raw.split(",") if s.strip()]


def bulk_resolve(
    action_ids: list[str],
    task_ids: list[str],
    action_state,
    task_svc,
    skip_task_id: str = "",
    actor_id: str = "",
    contact_outcome: Optional[str] = None,
    *,
    party_id: str,
    authz: AuthorizationService,
) -> None:
    """Dismiss action_ids + mark task_ids done — outcome-aware (delegates to
    application.activity_side_effects.resolve_actions_and_tasks, the SAME gate
    execute_side_effects() step 7 uses, per phase-02 Amendment: this endpoint
    (`/reason/resolve-async`, the cockpit's "+Nhắn Zalo" follow-up button) used
    to dismiss/complete unconditionally, silently undoing the snooze that step
    7 had just applied for the same no_answer/busy outcome).

    Parameters
    ----------
    action_ids:
        IDs to dismiss (or snooze, if contact_outcome is a no-contact outcome)
        via ``action_state``.
    task_ids:
        IDs to transition via ``task_svc.transition_status(…, 'done')`` — skipped
        entirely (left open) when contact_outcome is a no-contact outcome.
    action_state:
        ActionStateWriter (may be None → step skipped entirely).
    task_svc:
        TaskService (may be None → step skipped entirely).
    skip_task_id:
        task_id already handled by the single-task ``complete_task=1`` path;
        excluded here to avoid double-resolution.
    actor_id:
        user_id of the acting staff member passed to dismiss/snooze for audit
        log. Empty string is normalised to None.
    contact_outcome:
        the current activity's contact_outcome, if known (e.g. threaded from
        S.chosenOutcome in the cockpit JS). None/absent → treated like any
        other non-no-contact outcome (prior dismiss+done behavior), matching
        every pre-amendment caller that doesn't pass it.
    party_id:
        the party this resolve request is scoped to (the /reason/resolve-async
        route's own party_id path segment) — every action_id/task_id is
        verified to genuinely resolve to this party before mutation (phase-03
        IDOR fix); mismatches are skipped, not mutated.
    authz:
        shared AuthorizationService instance used for the party-match check.
    """
    filtered_task_ids = [
        tid for tid in task_ids if not (skip_task_id and tid == skip_task_id)
    ]
    resolve_actions_and_tasks(
        action_ids, filtered_task_ids, action_state, task_svc,
        contact_outcome, actor_id or None,
        party_id=party_id, authz=authz,
    )
