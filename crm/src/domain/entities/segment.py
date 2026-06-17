"""CRM Segment, SegmentMember, Campaign, and CampaignTarget domain entities.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Segment member source constants
# ---------------------------------------------------------------------------
MEMBER_SOURCE_RULE = "rule"
MEMBER_SOURCE_MANUAL = "manual"
VALID_MEMBER_SOURCES = [MEMBER_SOURCE_RULE, MEMBER_SOURCE_MANUAL]

# ---------------------------------------------------------------------------
# Segment rule keys whitelist
# ---------------------------------------------------------------------------
ALLOWED_RULE_KEYS = {
    "value_group",
    "customer_status",
    "days_since_last_order_gte",
    "channel_preference",
}

# ---------------------------------------------------------------------------
# Campaign objective constants
# ---------------------------------------------------------------------------
CAMPAIGN_OBJECTIVE_REACTIVATION = "reactivation"
CAMPAIGN_OBJECTIVE_WINBACK = "winback"
CAMPAIGN_OBJECTIVE_UPSELL = "upsell"
CAMPAIGN_OBJECTIVE_CROSSSELL = "crosssell"
VALID_CAMPAIGN_OBJECTIVES = [
    CAMPAIGN_OBJECTIVE_REACTIVATION,
    CAMPAIGN_OBJECTIVE_WINBACK,
    CAMPAIGN_OBJECTIVE_UPSELL,
    CAMPAIGN_OBJECTIVE_CROSSSELL,
]

# ---------------------------------------------------------------------------
# Campaign status constants
# ---------------------------------------------------------------------------
CAMPAIGN_STATUS_DRAFT = "draft"
CAMPAIGN_STATUS_RUNNING = "running"
CAMPAIGN_STATUS_DONE = "done"
VALID_CAMPAIGN_STATUSES = [
    CAMPAIGN_STATUS_DRAFT,
    CAMPAIGN_STATUS_RUNNING,
    CAMPAIGN_STATUS_DONE,
]

# Allowed campaign status transitions: current → reachable next statuses
CAMPAIGN_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    CAMPAIGN_STATUS_DRAFT: [CAMPAIGN_STATUS_RUNNING],
    CAMPAIGN_STATUS_RUNNING: [CAMPAIGN_STATUS_DONE],
    CAMPAIGN_STATUS_DONE: [],  # terminal
}

# ---------------------------------------------------------------------------
# Campaign target status constants
# ---------------------------------------------------------------------------
TARGET_STATUS_QUEUED = "queued"
TARGET_STATUS_SENT = "sent"
TARGET_STATUS_RESPONDED = "responded"
TARGET_STATUS_CONVERTED = "converted"
TARGET_STATUS_SKIPPED = "skipped"
VALID_TARGET_STATUSES = [
    TARGET_STATUS_QUEUED,
    TARGET_STATUS_SENT,
    TARGET_STATUS_RESPONDED,
    TARGET_STATUS_CONVERTED,
    TARGET_STATUS_SKIPPED,
]

# Terminal target statuses — no further transitions allowed
TARGET_TERMINAL_STATUSES = {TARGET_STATUS_CONVERTED, TARGET_STATUS_SKIPPED}

# Allowed target status transitions
TARGET_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    TARGET_STATUS_QUEUED: [TARGET_STATUS_SENT, TARGET_STATUS_SKIPPED],
    TARGET_STATUS_SENT: [TARGET_STATUS_RESPONDED, TARGET_STATUS_CONVERTED, TARGET_STATUS_SKIPPED],
    TARGET_STATUS_RESPONDED: [TARGET_STATUS_CONVERTED, TARGET_STATUS_SKIPPED],
    TARGET_STATUS_CONVERTED: [],
    TARGET_STATUS_SKIPPED: [],
}


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    """Groups parties by shared criteria (static or dynamic/rule-based)."""
    segment_id: str
    name: str
    is_dynamic: bool
    created_at: str
    updated_at: str
    description: Optional[str] = None
    definition: Optional[dict] = None      # parsed rule blob; None for static segments
    owner_user_id: Optional[str] = None
    member_count: int = 0


@dataclass
class SegmentMember:
    """Records a party's membership in a segment."""
    segment_id: str
    party_id: str
    source: str     # rule|manual
    added_at: str


@dataclass
class Campaign:
    """Reactivation / winback / upsell / cross-sell effort targeting a segment."""
    campaign_id: str
    name: str
    objective: str  # reactivation|winback|upsell|crosssell
    channel: str
    status: str     # draft|running|done
    created_at: str
    updated_at: str
    segment_id: Optional[str] = None
    scheduled_at: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class CampaignTarget:
    """One party in a campaign's outreach list."""
    campaign_id: str
    party_id: str
    status: str     # queued|sent|responded|converted|skipped
    assigned_user_id: Optional[str] = None
    last_touch_at: Optional[str] = None
    converted_order_code: Optional[str] = None
    converted_revenue_vnd: Optional[int] = None
    converted_at: Optional[str] = None


@dataclass
class CampaignROI:
    """Summary output of get_campaign_roi — aggregated conversion metrics."""
    campaign_id: str
    total_targets: int
    total_converted_revenue_vnd: int
    status_counts: dict[str, int] = field(default_factory=dict)
