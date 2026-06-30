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
ACTION_REORDER_PREEMPT = "REORDER_PREEMPT"
ACTION_WIN_BACK = "WIN_BACK"
ACTION_SECOND_ORDER = "SECOND_ORDER"
ACTION_HIGH_CANCEL_RISK = "HIGH_CANCEL_RISK"
ACTION_UPSELL = "UPSELL"
ACTION_CROSS_SELL = "CROSS_SELL"
ACTION_COLLECT_FEEDBACK = "COLLECT_FEEDBACK"
VALID_ACTION_TYPES = [
    ACTION_CALL_NOW,
    ACTION_REORDER_NUDGE,
    ACTION_REORDER_PREEMPT,
    ACTION_WIN_BACK,
    ACTION_SECOND_ORDER,
    ACTION_HIGH_CANCEL_RISK,
    ACTION_UPSELL,
    ACTION_CROSS_SELL,
    ACTION_COLLECT_FEEDBACK,
]

CANCEL_RISK_THRESHOLD: float = 0.10
ACTION_QUEUE_CHECKLIST_THRESHOLD: int = 2

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
    # Discount bucket metrics (4 buckets × 2 metrics; 0.0–1.0; None = never had this type)
    last_line_discount_rate:       float | None = None
    max_line_discount_rate:        float | None = None
    last_voucher_discount_rate:    float | None = None
    max_voucher_discount_rate:     float | None = None
    last_campaign_discount_rate:   float | None = None
    max_campaign_discount_rate:    float | None = None
    last_negotiated_discount_rate: float | None = None
    max_negotiated_discount_rate:  float | None = None

    @property
    def is_high_cancel_risk(self) -> bool:
        return self.cancel_rate > CANCEL_RISK_THRESHOLD


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
    customer_id: Optional[int] = None   # warehouse natural key from wh_customer_base; None when base row absent
    status: str = "open"                # open|dismissed|snoozed (from crm_action_state)
    snoozed_until: Optional[str] = None # YYYY-MM-DD; set when status = 'snoozed'
    top_affinity_product: str = ""      # product customer buys most (for CS context + search)
    last_purchased_product: str = ""    # product from customer's last order (for CS context + search)
    # SKU-level purchase context (populated for SKU actions only; empty for customer-level actions)
    last_purchase_date: str = ""        # YYYY-MM-DD of the most recent purchase of this SKU
    last_order_code: str = ""           # order_code aligned with last_purchase_date (same grain)
    last_sku_discount_rate: Optional[float] = None  # 0.0–1.0; None when no discount data
    last_net_unit_price: Optional[int] = None       # VND per base unit (VAT-exclusive, after all discounts)
    estimated_depletion_date: str = ""  # YYYY-MM-DD when supply runs out (SKU actions only)


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
class CustomerTier:
    """Strategic tier row from wh_customer_tier (mart_customer_tier sync)."""
    customer_key: str
    customer_id: int
    strategic_tier: str          # LIVE_CORE|SECOND_ORDER|DORMANT_VALUABLE|LAPSED_VALUABLE|MASKED_REPEAT|NONBUYER|GRAVEYARD
    tier_reason: str
    recency_days: int
    order_count: int
    value_group: str
    is_contactable: bool
    tier_generated_at: str


@dataclass
class CacheInsight:
    """Composed read model returned by get_customer_insight.

    None pointer fields mean the cache is empty or the customer was not found.
    """
    refreshed_at: str = ""                              # from insight.refreshed_at or empty
    insight: Optional[CustomerInsight] = None           # None when no insight row exists
    tier: Optional[CustomerTier] = None                 # None when mart_customer_tier not yet synced
    actions: list[ActionQueueItem] = field(default_factory=list)
    recent_orders: list[RecentOrder] = field(default_factory=list)

    @property
    def sorted_actions(self) -> list[ActionQueueItem]:
        """User-level actions (no SKU/last_purchase_date) first; SKU actions newest first."""
        nodal = [a for a in self.actions if not a.last_purchase_date]
        dated = sorted(
            [a for a in self.actions if a.last_purchase_date],
            key=lambda a: a.last_purchase_date,
            reverse=True,
        )
        return nodal + dated

    @property
    def has_active_actions(self) -> bool:
        return any(a.status != ACTION_STATUS_DISMISSED for a in self.actions)

    def unresolved_count(self, resolved_ids: set) -> int:
        return sum(
            1 for a in self.actions
            if a.status != ACTION_STATUS_DISMISSED and a.action_id not in resolved_ids
        )

    def best_next_purchase_display(self, today: str) -> Optional[str]:
        """Return the soonest future or most recent past next-purchase date.

        Candidates: non-dismissed action depletion dates + insight.predicted_next_purchase_date.
        today: YYYY-MM-DD string — ISO-8601 lexicographic comparison is correct.
        """
        best_future: Optional[str] = None
        best_past: Optional[str] = None
        candidates = [
            a.estimated_depletion_date
            for a in self.actions
            if a.estimated_depletion_date and a.status != ACTION_STATUS_DISMISSED
        ]
        if self.insight and self.insight.predicted_next_purchase_date:
            candidates.append(self.insight.predicted_next_purchase_date)
        for d in candidates:
            if d >= today:
                if best_future is None or d < best_future:
                    best_future = d
            else:
                if best_past is None or d > best_past:
                    best_past = d
        return best_future if best_future is not None else best_past


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

    @property
    def abbreviation(self) -> str:
        return {"ACTIVE": "A", "AT_RISK": "R", "CHURNED": "C"}.get(
            (self.status or "").upper(), "·"
        )


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


# ---------------------------------------------------------------------------
# Live dim_customers segments + aggregated profitability/returns metrics
# ---------------------------------------------------------------------------

@dataclass
class CustomerDimMetrics:
    """Live dim_customers behavior segments + aggregated value metrics.

    Fetched on demand from olap.duckdb — never cached in SQLite.
    All monetary values are float VND. Degrades gracefully to None when absent.
    """
    customer_key: str = ""
    lifecycle_stage: str = ""
    product_affinity: str = ""
    payment_behavior: str = ""
    geo_region: str = ""
    customer_type: str = ""
    cohort_month: str = ""          # first 7 chars of first_order_date (YYYY-MM)
    total_gross_profit: Optional[float] = None
    total_cogs: Optional[float] = None
    avg_gross_margin_pct: Optional[float] = None
    cogs_order_count: Optional[int] = None
    order_count: Optional[int] = None
    total_return_amount: Optional[float] = None
    return_count: Optional[int] = None

    @property
    def cogs_coverage_pct(self) -> Optional[int]:
        if self.cogs_order_count is None or not self.order_count:
            return None
        return round(self.cogs_order_count / self.order_count * 100)

    @property
    def has_partial_cogs_coverage(self) -> bool:
        return (
            self.cogs_order_count is not None
            and bool(self.order_count)
            and self.cogs_order_count < self.order_count
        )
