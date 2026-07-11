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
# Kind constants
# ---------------------------------------------------------------------------
TASK_KIND_CONTACT = "contact"    # outreach to a customer
TASK_KIND_INTERNAL = "internal"  # internal/admin work (e.g. verify_account)
TASK_KIND_GENERIC = "generic"    # no customer party (manual, no party_id)
VALID_TASK_KINDS = [TASK_KIND_CONTACT, TASK_KIND_INTERNAL, TASK_KIND_GENERIC]

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
# unclaim reason constants ("Trả việc") — flat code-string list, matching
# activity.py's VALID_OUTCOME_REASONS shape exactly (every VALID_* constant in
# this codebase is a flat list, not (code, label) tuples). Kept intentionally
# short — this is a lightweight audit signal, not a taxonomy project (YAGNI).
# VN labels live in UNCLAIM_REASON_LABELS below (consumed by TaskService when
# composing the audit-note body) — templates render their own VN-labeled
# <select> options directly (matching this codebase's existing reason-picker
# convention, e.g. c360_call_cockpit_panel.html's REFUSAL_REASON_PILLS), not
# threaded through context.
# ---------------------------------------------------------------------------
VALID_UNCLAIM_REASONS = [
    "wrong_region", "wrong_specialty", "duplicate_lead",
    "reassign_colleague", "other",
]

UNCLAIM_REASON_LABELS: dict[str, str] = {
    "wrong_region": "Sai khu vực",
    "wrong_specialty": "Sai chuyên môn/nhu cầu",
    "duplicate_lead": "Lead trùng lặp",
    "reassign_colleague": "Chuyển cho đồng nghiệp",
    "other": "Khác",
}

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
    task_kind: str = "contact"              # contact|internal|generic (set by migration/derive)
    channel: Optional[str] = None          # reserved: phone|zalo|messenger|email|store
    # Action-queue claim context — set once at claim time (migration 0036)
    value_at_stake_vnd: Optional[int] = None   # SUM of all actions' value_at_stake_vnd
    top_affinity_product: Optional[str] = None  # product name from highest-value action
    # Migration 0043 — JSON array string of action_type(s) claimed, snapshotted ONCE
    # at claim time (action_queue_claim source only). NULL for pre-migration rows and
    # non-claim sources. See TaskService.claim_customer_actions.
    claimed_action_types: Optional[str] = None
    # Denormalised display fields — populated by list queries via LEFT JOIN
    party_name: Optional[str] = None        # crm_party.display_name
    assignee_name: Optional[str] = None     # crm_app_user.full_name

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
