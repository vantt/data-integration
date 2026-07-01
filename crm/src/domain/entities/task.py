"""CRM Task domain entity — follow-up work items assigned to staff.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------
TASK_STATUS_OPEN = "open"
TASK_STATUS_DOING = "doing"
TASK_STATUS_DONE = "done"
TASK_STATUS_CANCELLED = "cancelled"
VALID_TASK_STATUSES = [
    TASK_STATUS_OPEN,
    TASK_STATUS_DOING,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
]

# ---------------------------------------------------------------------------
# Source constants
# ---------------------------------------------------------------------------
TASK_SOURCE_MANUAL = "manual"
TASK_SOURCE_ACTION_QUEUE = "action_queue"
TASK_SOURCE_ACTION_QUEUE_CLAIM = "action_queue_claim"  # per-customer claim (1 task covers all actions)
TASK_SOURCE_CAMPAIGN = "campaign"
VALID_TASK_SOURCES = [TASK_SOURCE_MANUAL, TASK_SOURCE_ACTION_QUEUE, TASK_SOURCE_ACTION_QUEUE_CLAIM, TASK_SOURCE_CAMPAIGN]

# ---------------------------------------------------------------------------
# Priority constants (0 = normal, higher = more urgent)
# ---------------------------------------------------------------------------
TASK_PRIORITY_NORMAL = 0
TASK_PRIORITY_HIGH = 1
TASK_PRIORITY_URGENT = 2

# ---------------------------------------------------------------------------
# Allowed status transitions: current → set of reachable next statuses
# ---------------------------------------------------------------------------
TASK_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    TASK_STATUS_OPEN: [TASK_STATUS_DOING, TASK_STATUS_DONE, TASK_STATUS_CANCELLED],
    TASK_STATUS_DOING: [TASK_STATUS_DONE, TASK_STATUS_CANCELLED, TASK_STATUS_OPEN],
    TASK_STATUS_DONE: [TASK_STATUS_OPEN],       # allow re-open
    TASK_STATUS_CANCELLED: [TASK_STATUS_OPEN],  # allow re-open
}


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Follow-up work item assigned to a staff member.

    Tasks can be created manually or auto-generated from wh_action_queue.
    """
    task_id: str                # UUID
    title: str
    priority: int               # 0=normal, higher=more urgent
    status: str                 # open|doing|done|cancelled
    source: str                 # manual|action_queue|campaign
    created_at: str             # UTC ISO-8601
    updated_at: str             # UTC ISO-8601
    party_id: Optional[str] = None          # FK → crm_party (nullable)
    description: Optional[str] = None
    due_at: Optional[str] = None            # UTC ISO-8601 nullable
    assignee_user_id: Optional[str] = None  # FK → crm_app_user nullable
    source_ref: Optional[str] = None        # action_id or campaign_id (idempotency key)
    created_by: Optional[str] = None        # FK → crm_app_user nullable
    completed_at: Optional[str] = None      # UTC ISO-8601 nullable

    @property
    def priority_label(self) -> str:
        if self.priority >= TASK_PRIORITY_URGENT:
            return "P1"
        if self.priority == TASK_PRIORITY_HIGH:
            return "P2"
        return "P3"

    def is_overdue_at(self, now_utc: str) -> bool:
        """True when due_at is set and earlier than the given UTC ISO-8601 timestamp."""
        return bool(self.due_at) and bool(now_utc) and self.due_at < now_utc
