"""outcome_resolve_helpers.py — pure-logic helpers for Phase-04 outcome bulk-resolve.

No FastAPI / web dependency — imported by both the activity routes module and the
pure-logic unit tests (which run outside Docker where fastapi is absent).
"""
from __future__ import annotations

import logging
from typing import Optional

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
) -> None:
    """Dismiss action_ids + mark task_ids done. Per-item failures are logged, never raised.

    Parameters
    ----------
    action_ids:
        IDs to dismiss via ``action_state.dismiss()``.
    task_ids:
        IDs to transition via ``task_svc.transition_status(…, 'done')``.
    action_state:
        ActionStateWriter (may be None → step skipped entirely).
    task_svc:
        TaskService (may be None → step skipped entirely).
    skip_task_id:
        task_id already handled by the single-task ``complete_task=1`` path;
        excluded here to avoid double-resolution.
    actor_id:
        user_id of the acting staff member passed to dismiss for audit log.
        Empty string is normalised to None.
    """
    uid: Optional[str] = actor_id or None

    if action_state is not None:
        for aid in action_ids:
            try:
                action_state.dismiss(aid, user_id=uid)
            except Exception as exc:
                log.warning("bulk_resolve: dismiss action %s: %s", aid, exc)

    if task_svc is not None:
        for tid in task_ids:
            if skip_task_id and tid == skip_task_id:
                continue
            try:
                task_svc.transition_status(tid, "done")
            except Exception as exc:
                log.warning("bulk_resolve: transition task %s: %s", tid, exc)
