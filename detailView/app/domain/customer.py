"""Customer insight aggregate — the complete single-customer view.

Field names mirror dim_customers + mart_customer_status_snapshot_monthly (researcher-02).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from .shared import Badge, DataQualityFlag, Tone, safe_ratio


@dataclass
class CustomerAction:
    """One outreach action row from mart_customer_action_queue."""

    action_type: str
    priority_rank: int
    action_rationale: str | None = None
    value_at_stake: Decimal | None = None
    avg_order_value: Decimal | None = None
    avg_days_between_orders: int | None = None
    next_purchase_signal: str | None = None
    discount_sensitivity: str | None = None
    predicted_next_purchase_date: date | None = None
    cancel_rate: float | None = None
    recency_days: int | None = None

RETAIL = "RETAIL"


@dataclass
class CustomerProfile:
    customer_id: str
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    dob: date | None = None
    sex: str | None = None
    address1: str | None = None
    ward: str | None = None
    district: str | None = None
    province: str | None = None
    country: str | None = None
    geo_region: str | None = None
    loyalty_point: int | None = None
    customer_type: str | None = None
    customer_group: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class CustomerValueMetrics:
    lifetime_value: Decimal | None = None
    order_count: int | None = None
    value_group: str | None = None
    # Aggregated over the customer's orders (computed by the repository query)
    total_gross_profit: Decimal | None = None
    total_cogs: Decimal | None = None
    avg_gross_margin_pct: float | None = None
    total_return_amount: Decimal | None = None
    return_count: int | None = None
    cogs_order_count: int | None = None  # orders with has_cogs, for coverage caveat

    @property
    def aov(self) -> float | None:
        return safe_ratio(self.lifetime_value, self.order_count)


@dataclass
class CustomerBehavior:
    recency_days: int | None = None
    frequency: int | None = None  # = order_count
    monetary: Decimal | None = None  # = lifetime_value
    lifecycle_stage: str | None = None
    channel_preference: str | None = None
    product_affinity: str | None = None
    payment_behavior: str | None = None
    geo_region: str | None = None
    customer_type: str | None = None
    first_order_date: datetime | None = None
    last_order_date: datetime | None = None
    lifespan_days: int | None = None

    @property
    def cohort_month(self) -> str | None:
        return self.first_order_date.strftime("%Y-%m") if self.first_order_date else None


@dataclass
class StatusSnapshot:
    snapshot_month: date | None = None
    status: str | None = None  # ACTIVE / AT_RISK / CHURNED
    is_new: bool = False
    days_since_last_order: int | None = None
    value_group: str | None = None


@dataclass
class OrderSummary:
    """One row in a customer's order history (links to /orders/{order_code})."""

    order_code: str
    order_date: datetime | None = None
    status: str | None = None
    channel_name: str | None = None
    seller_name: str | None = None
    total_collected: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin_pct: float | None = None
    payment_label: str | None = None
    has_return: bool = False
    carrier_id: str | None = None


@dataclass
class CustomerDetail:
    profile: CustomerProfile
    value_metrics: CustomerValueMetrics = field(default_factory=lambda: CustomerValueMetrics())
    behavior: CustomerBehavior = field(default_factory=CustomerBehavior)
    status_timeline: list[StatusSnapshot] = field(default_factory=list)
    order_history: list[OrderSummary] = field(default_factory=list)
    actions: list[CustomerAction] = field(default_factory=list)

    @property
    def has_actions(self) -> bool:
        return bool(self.actions)

    @property
    def is_retail(self) -> bool:
        return (self.profile.customer_type or "").upper() == RETAIL

    @property
    def timeline_available(self) -> bool:
        """Status snapshot mart is RETAIL-only; show a notice otherwise."""
        return self.is_retail

    def identity_badges(self) -> list[Badge]:
        out: list[Badge] = []
        value_tone = {
            "VALUE_VIP": Tone.GOOD, "VALUE_GOLD": Tone.GOOD,
            "VALUE_SILVER": Tone.NEUTRAL, "VALUE_BRONZE": Tone.NEUTRAL,
        }
        lifecycle_tone = {
            "LIFECYCLE_ACTIVE": Tone.GOOD, "LIFECYCLE_NEW": Tone.GOOD,
            "LIFECYCLE_AT_RISK": Tone.WARN, "LIFECYCLE_CHURNED": Tone.BAD,
        }
        if self.profile.customer_type:
            out.append(Badge(self.profile.customer_type, Tone.NEUTRAL, "customer_type"))
        if self.value_metrics.value_group:
            out.append(Badge(self.value_metrics.value_group,
                             value_tone.get(self.value_metrics.value_group, Tone.NEUTRAL), "value"))
        if self.behavior.lifecycle_stage:
            out.append(Badge(self.behavior.lifecycle_stage,
                             lifecycle_tone.get(self.behavior.lifecycle_stage, Tone.NEUTRAL), "lifecycle"))
        return out

    def quality_flags(self, cap=None, dq=None) -> list[DataQualityFlag]:
        """Compute per-customer data-quality flags.

        Args:
            cap: Optional CapabilityPort (reserved for future capability checks).
            dq: Optional DataQualitySummary. When provided, acq_unknown is conditional:
                only emitted when acq_source_null_rate_pct > 95 (or None). This lets the
                flag self-silence if the pipeline ever starts populating acquisition source.
        """
        flags: list[DataQualityFlag] = []
        # acq_unknown: self-healing — silences when pipeline populates acquisition source.
        # Without dq we can't know the rate, so we emit it conservatively.
        if dq is None or dq.acq_source_null_rate_pct is None or dq.acq_source_null_rate_pct > 95.0:
            flags.append(DataQualityFlag("acq_unknown", "Acquisition source not tracked", "info"))
        # nightly_sync: permanent — pipeline cadence is configuration, not a data signal.
        flags.append(DataQualityFlag("nightly_sync", "Profile syncs nightly (not real-time)", "info"))
        if not self.is_retail:
            flags.append(DataQualityFlag("timeline_retail", "Status timeline: RETAIL customers only", "info"))
        vm = self.value_metrics
        if vm.cogs_order_count is not None and vm.order_count:
            if vm.cogs_order_count < vm.order_count:
                flags.append(DataQualityFlag("cogs_partial", "Margin from partial COGS coverage", "warn"))
        return flags
