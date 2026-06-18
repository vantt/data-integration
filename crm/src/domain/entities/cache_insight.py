"""CRM cache insight entities — pre-computed warehouse signals cached in cache.db.

Read-only view of data computed in the warehouse; CRM never recomputes these.
Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Value group constants (RFM tiers)
# ---------------------------------------------------------------------------
VALUE_GROUP_VIP = "VIP"
VALUE_GROUP_GOLD = "GOLD"
VALUE_GROUP_SILVER = "SILVER"
VALUE_GROUP_BRONZE = "BRONZE"
VALID_VALUE_GROUPS = [VALUE_GROUP_VIP, VALUE_GROUP_GOLD, VALUE_GROUP_SILVER, VALUE_GROUP_BRONZE]

# ---------------------------------------------------------------------------
# Customer status constants
# ---------------------------------------------------------------------------
CUSTOMER_STATUS_ACTIVE = "active"
CUSTOMER_STATUS_AT_RISK = "at_risk"
CUSTOMER_STATUS_CHURNED = "churned"
VALID_CUSTOMER_STATUSES = [CUSTOMER_STATUS_ACTIVE, CUSTOMER_STATUS_AT_RISK, CUSTOMER_STATUS_CHURNED]

# ---------------------------------------------------------------------------
# Next purchase signal constants
# ---------------------------------------------------------------------------
SIGNAL_OVERDUE = "OVERDUE"
SIGNAL_DUE_SOON = "DUE_SOON"
SIGNAL_ON_TRACK = "ON_TRACK"

# ---------------------------------------------------------------------------
# Discount sensitivity constants
# ---------------------------------------------------------------------------
SENSITIVITY_HIGH = "HIGH"
SENSITIVITY_MEDIUM = "MEDIUM"
SENSITIVITY_LOW = "LOW"

# ---------------------------------------------------------------------------
# Action type constants (wh_action_queue)
# ---------------------------------------------------------------------------
ACTION_CALL_NOW = "CALL_NOW"
ACTION_REORDER_NUDGE = "REORDER_NUDGE"
ACTION_WIN_BACK = "WIN_BACK"
ACTION_UPSELL = "UPSELL"
ACTION_CROSS_SELL = "CROSS_SELL"
ACTION_COLLECT_FEEDBACK = "COLLECT_FEEDBACK"
VALID_ACTION_TYPES = [
    ACTION_CALL_NOW,
    ACTION_REORDER_NUDGE,
    ACTION_WIN_BACK,
    ACTION_UPSELL,
    ACTION_CROSS_SELL,
    ACTION_COLLECT_FEEDBACK,
]

# ---------------------------------------------------------------------------
# Action lifecycle status constants (crm_action_state)
# ---------------------------------------------------------------------------
ACTION_STATUS_OPEN = "open"
ACTION_STATUS_DISMISSED = "dismissed"
ACTION_STATUS_SNOOZED = "snoozed"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class CustomerInsight:
    """Pre-computed RFM + behavioural signals cached from wh_customer_insight.

    All monetary values are VND integers.
    Margins use realized_margin_pct (H010-corrected).
    """
    customer_key: str
    customer_id: int
    value_group: str                    # VIP|GOLD|SILVER|BRONZE
    customer_status: str                # active|at_risk|churned
    next_purchase_signal: str           # OVERDUE|DUE_SOON|ON_TRACK
    avg_days_between_orders: float
    avg_order_spend: float
    discount_sensitivity: str           # HIGH|MEDIUM|LOW
    cancel_rate: float
    lifetime_contribution_margin: float
    is_margin_negative: bool
    refreshed_at: str
    first_order_date: str = ""               # YYYY-MM-DD from wh_customer_base; empty when absent
    predicted_next_purchase_date: str = ""  # YYYY-MM-DD or empty
    last_purchased_sku: str = ""
    top_affinity_product: str = ""
    second_affinity_product: str = ""
    channel_preference: str = ""


@dataclass
class ActionQueueItem:
    """One recommended action from the warehouse action queue (wh_action_queue)."""
    action_id: str
    customer_key: str
    action_type: str        # CALL_NOW|REORDER_NUDGE|WIN_BACK|UPSELL|CROSS_SELL|COLLECT_FEEDBACK
    rationale_vi: str       # Vietnamese rationale text
    value_at_stake_vnd: int
    priority: int
    pending_since: str      # YYYY-MM-DD; first day this episode appeared
    generated_date: str     # YYYY-MM-DD; last warehouse refresh
    refreshed_at: str
    customer_name: str = ""             # display_name from wh_customer_base; empty when not found
    party_id: Optional[str] = None      # CRM party_id resolved via crm_party_identity; None when not synced
    status: str = "open"                # open|dismissed|snoozed (from crm_action_state)
    snoozed_until: Optional[str] = None # YYYY-MM-DD; set when status = 'snoozed'


@dataclass
class RecentOrder:
    """Slim order header row from wh_order_hdr."""
    order_id: str
    order_code: str
    customer_id: int
    date_key: int           # ICT YYYYMMDD (pass-through from warehouse)
    net_revenue: int        # VND INTEGER (VAT-inclusive)
    status: str
    channel: str
    item_count: int


@dataclass
class CacheInsight:
    """Composed read model returned by get_customer_insight.

    None pointer fields mean the cache is empty or the customer was not found.
    """
    refreshed_at: str = ""                              # from insight.refreshed_at or empty
    insight: Optional[CustomerInsight] = None           # None when no insight row exists
    actions: list[ActionQueueItem] = field(default_factory=list)
    recent_orders: list[RecentOrder] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Status timeline snapshot (mart_customer_status_snapshot_monthly)
# ---------------------------------------------------------------------------

@dataclass
class StatusSnapshot:
    """One monthly status snapshot from mart_customer_status_snapshot_monthly.

    snapshot_month: ISO date string 'YYYY-MM-DD' (first day of month).
    status: 'ACTIVE' | 'AT_RISK' | 'CHURNED' | ''.
    days_since_last_order: int or None when not available.
    value_group: 'VIP'|'GOLD'|'SILVER'|'BRONZE'|''.
    is_new: True when this was the customer's acquisition month.
    """
    snapshot_month: str
    status: str
    days_since_last_order: Optional[int]
    value_group: str
    is_new: bool


# ---------------------------------------------------------------------------
# Live order row from DuckDB (fact_orders × economics × dims)
# ---------------------------------------------------------------------------

@dataclass
class CustomerOrderRow:
    """Full order row fetched from olap.duckdb — richer than RecentOrder.

    Monetary values are float VND (from DuckDB DOUBLE cast).
    gross_margin_pct is a ratio (0.0–1.0); None when economics unavailable.
    """
    order_code: str
    created_at: str          # ISO datetime string (ICT)
    status: str
    channel_name: str
    seller_name: str
    total_collected: float
    gross_profit: Optional[float]
    gross_margin_pct: Optional[float]
    payment_label: str
    has_return: bool
