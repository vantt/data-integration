"""Application helper — derive_task_kind: pure function mapping task context to a kind.

No IO, no imports from adapters.
"""
from __future__ import annotations

from domain.entities.cache_insight import ACTION_COLLECT_FEEDBACK
from domain.entities.task import (
    TASK_KIND_CONTACT,
    TASK_KIND_GENERIC,
    TASK_KIND_INTERNAL,
    TASK_SOURCE_ACTION_QUEUE,
    TASK_SOURCE_ACTION_QUEUE_CLAIM,
)

# Action types from the warehouse that are internal-only (feedback/review tasks
# directed at internal staff rather than outreach to a customer).
_INTERNAL_ACTION_TYPES: frozenset[str] = frozenset({
    ACTION_COLLECT_FEEDBACK,
})

# Sources that unconditionally map to internal regardless of party presence.
_INTERNAL_SOURCES: frozenset[str] = frozenset({
    "verify_account",
})


def derive_task_kind(
    source: str,
    source_ref: str | None,
    party_id: str | None,
    action_type: str | None = None,
) -> tuple[str, bool]:
    """Return (task_kind, confident) for a task being created.

    Parameters
    ----------
    source:      task source string (manual | action_queue | action_queue_claim | …)
    source_ref:  optional idempotency reference (action_id, verify_account/... etc.)
    party_id:    CRM party FK; None → no customer attached
    action_type: warehouse action type (CALL_NOW | REORDER_NUDGE | … | COLLECT_FEEDBACK)
                 Only relevant when source is action_queue / action_queue_claim.

    Returns
    -------
    task_kind:  one of 'contact' | 'internal' | 'generic'
    confident:  True when derivation is deterministic; False when best-guess (M05 reveals selector)
    """
    # Rule 1: no customer party → generic (no outreach is possible)
    if not party_id:
        return TASK_KIND_GENERIC, True

    # Rule 2: known internal source or source_ref prefix
    if source in _INTERNAL_SOURCES:
        return TASK_KIND_INTERNAL, True

    if source_ref and source_ref.startswith("verify_account"):
        return TASK_KIND_INTERNAL, True

    # Rule 3: action_queue sources — map by action_type
    if source in (TASK_SOURCE_ACTION_QUEUE, TASK_SOURCE_ACTION_QUEUE_CLAIM):
        if action_type and action_type in _INTERNAL_ACTION_TYPES:
            return TASK_KIND_INTERNAL, True
        return TASK_KIND_CONTACT, True  # all outreach action types → contact

    # Rule 4: manual task with a party — best guess contact, not confident
    # (staff may mean internal follow-up; M05 shows the selector)
    if source == "manual":
        return TASK_KIND_CONTACT, False

    # Fallback: party present but unknown source → contact (best guess, not confident)
    return TASK_KIND_CONTACT, False
