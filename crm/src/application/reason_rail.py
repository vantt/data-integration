"""Application helper — Reason Rail assembly for S14 Call Cockpit.

Merges two signal sources into a ranked rail:
  1. insight.sorted_actions (warehouse action queue items, open/not-dismissed)
  2. open/doing CONTACT tasks from task_repo (task_kind=contact)

Output:
  primary   : single RailItem | None  — the ripest item
  secondary : list[RailItem]          — remaining items in ripeness order

Each RailItem carries provenance so the outcome handler knows what to resolve:
  - action_id  set  → dismiss via action_state + optionally flip task status
  - task_id    set  → flip task.status via task_service.transition_status

Ripeness ordering heuristic (highest priority = smallest score):
  1. Task items in 'doing' status (actively being worked)
  2. Action queue items with CALL_NOW type
  3. Task items in 'open' status
  4. Action queue items by their own priority field (higher = more urgent)
  5. Tie-break: pending_since / due_at ascending (earlier = more urgent)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── RailItem ──────────────────────────────────────────────────────────────────

@dataclass
class RailItem:
    """One resolved rail entry carrying display data and provenance keys."""
    # Display
    label: str                     # human-readable action/task title
    rationale: str                 # why this action/task is on the rail
    action_type: str               # CALL_NOW | REORDER_NUDGE | task_kind, etc.
    priority: int                  # higher = more urgent (domain priority)
    pending_since: str             # YYYY-MM-DD or "" — for display + sorting

    # Provenance (exactly one of these is set)
    action_id: Optional[str] = None   # from wh_action_queue row
    task_id: Optional[str] = None     # from crm_task row

    # Task-specific metadata (only when task_id is set)
    task_status: str = ""          # open | doing

    # Action-specific metadata (only when action_id is set)
    value_at_stake_vnd: int = 0

    # Extra context for UI
    extra: dict = field(default_factory=dict)

    @property
    def ripeness_key(self) -> tuple:
        """Tuple for ascending sort — smallest = ripest (show first).

        Tier 0: doing tasks (already being worked — highest priority)
        Tier 1: CALL_NOW action items
        Tier 2: open tasks
        Tier 3: other action queue items
        Within tier: negate priority then pending_since ascending.
        """
        if self.task_id and self.task_status == "doing":
            tier = 0
        elif self.action_id and self.action_type == "CALL_NOW":
            tier = 1
        elif self.task_id:
            tier = 2
        else:
            tier = 3
        return (tier, -self.priority, self.pending_since or "9999-99-99")


# ── Assembly ──────────────────────────────────────────────────────────────────

def assemble_reason_rail(
    insight,                  # CacheInsight | None
    contact_tasks: list,      # list[Task] — already filtered kind=contact, status in open/doing
    resolved_action_ids: set | None = None,
    pinned_task_id: Optional[str] = None,  # from ?task_id= query param — force to PRIMARY
) -> tuple[Optional[RailItem], list[RailItem]]:
    """Build (primary, secondary[]) rail.

    Parameters
    ----------
    insight:
        CacheInsight from SQLite cache.  May be None.
    contact_tasks:
        Tasks already filtered to task_kind=contact, status in (open, doing).
    resolved_action_ids:
        Set of action_ids that already have an outcome (task done/cancelled).
        These are excluded from the rail.
    pinned_task_id:
        When provided (from ?task_id= query param), force that task to PRIMARY
        regardless of ripeness.
    """
    resolved = resolved_action_ids or set()
    items: list[RailItem] = []

    # 1. Warehouse action queue items (open, not resolved)
    if insight is not None:
        for action in insight.sorted_actions:
            status = getattr(action, "status", "open")
            if status == "dismissed":
                continue
            if getattr(action, "action_id", None) in resolved:
                continue
            items.append(RailItem(
                label=getattr(action, "action_type", ""),
                rationale=getattr(action, "rationale_vi", ""),
                action_type=getattr(action, "action_type", ""),
                priority=getattr(action, "priority", 0),
                pending_since=getattr(action, "pending_since", ""),
                action_id=getattr(action, "action_id", None),
                value_at_stake_vnd=getattr(action, "value_at_stake_vnd", 0),
                extra={
                    "top_affinity_product": getattr(action, "top_affinity_product", ""),
                    "last_purchased_product": getattr(action, "last_purchased_product", ""),
                },
            ))

    # 2. Open/doing contact-task items
    for task in contact_tasks:
        task_id = getattr(task, "task_id", None)
        task_status = getattr(task, "status", "open")
        due_at = getattr(task, "due_at", "") or ""
        pending_since = due_at[:10] if due_at else ""
        items.append(RailItem(
            label=getattr(task, "title", ""),
            rationale=getattr(task, "description", "") or "",
            action_type=getattr(task, "task_kind", "contact"),
            priority=getattr(task, "priority", 0),
            pending_since=pending_since,
            task_id=task_id,
            task_status=task_status,
        ))

    # Sort by ripeness (ascending ripeness_key = most urgent first)
    items.sort(key=lambda r: r.ripeness_key)

    if not items:
        return None, []

    # Handle pinned task: force it to PRIMARY position
    if pinned_task_id:
        pinned_idx = next(
            (i for i, r in enumerate(items) if r.task_id == pinned_task_id),
            None,
        )
        if pinned_idx is not None and pinned_idx != 0:
            pinned = items.pop(pinned_idx)
            items.insert(0, pinned)

    primary = items[0]
    secondary = items[1:]
    return primary, secondary
