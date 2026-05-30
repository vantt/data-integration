"""Shared value objects, enums, and small helpers used across the domain."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

CURRENCY_VND = "VND"


class Tone(str, Enum):
    NEUTRAL = "neutral"
    GOOD = "good"
    WARN = "warn"
    BAD = "bad"


@dataclass(frozen=True)
class Money:
    """Monetary amount. amount=None means unknown/not-applicable (render as '—')."""

    amount: Decimal | None
    currency: str = CURRENCY_VND

    @property
    def is_known(self) -> bool:
        return self.amount is not None


@dataclass(frozen=True)
class Badge:
    """A labelled chip. `kind` groups badges (status/payment/value/lifecycle/quality)."""

    label: str
    tone: Tone = Tone.NEUTRAL
    kind: str = ""


@dataclass(frozen=True)
class DataQualityFlag:
    """Inline caveat the UI must surface (never hide a data-truth issue)."""

    code: str
    label: str
    severity: str = "info"  # "info" | "warn"


# Tabs are consolidated by user task (fewer, fuller panels — see UI_SPECS §2.2/§3.2):
#   Order:    Financial(+cost breakdown) · Items · Operations(payments+fulfillment+returns) · Context(channel+staff+timeline)
#   Customer: Overview(value+behaviour) · Status Timeline · Order History
class OrderTab(str, Enum):
    FINANCIAL = "financial"      # revenue/profit waterfall + cost-ledger breakdown
    ITEMS = "items"              # line items / SKUs
    OPERATIONS = "operations"    # payments + fulfillment + returns (order lifecycle)
    CONTEXT = "context"          # channel & source + staff/team + timeline


class CustomerTab(str, Enum):
    OVERVIEW = "overview"            # value metrics + behaviour/RFM + segmentation
    STATUS_TIMELINE = "status-timeline"
    ORDER_HISTORY = "order-history"


@dataclass(frozen=True)
class CustomerHit:
    """Lightweight search result row for customer disambiguation."""

    customer_id: str
    full_name: str | None = None
    phone: str | None = None
    value_group: str | None = None


@dataclass
class SearchResolution:
    """Outcome of a header search. Web adapter maps this to redirect / dropdown / hint."""

    redirect_to: str | None = None
    customer_hits: list[CustomerHit] = field(default_factory=list)
    not_found: bool = False


def safe_ratio(numerator: Decimal | float | None, denominator: Decimal | float | None) -> float | None:
    """Percent-ready ratio guarding None and divide-by-zero. Returns fraction (0..1)."""
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


@dataclass(frozen=True)
class DataQualitySummary:
    """System-level coverage snapshot. Grain: entire dataset.

    Populated from mart_data_quality view (pipeline-refreshed) augmented with
    filesystem-derived data_version and stale_views from CapabilityAdapter.
    All rate fields are DOUBLE|None (None = view absent or no data).
    """

    # Filesystem-derived version token (lexically-max parquet basename)
    data_version: str
    # Timestamp from mart_data_quality.as_of_ict (pipeline run time)
    as_of: datetime | None
    # Aggregate counts/rates from mart_data_quality
    total_orders: int | None
    cogs_rate_pct: float | None
    platform_fees_rate_pct: float | None
    fulfillment_coverage_pct: float | None
    return_rate_pct: float | None
    us_share_pct: float | None
    carrier_null_rate_pct: float | None
    acq_source_null_rate_pct: float | None
    # Schema-derived signals (computed by CapabilityAdapter)
    stale_views: list[str]
    has_carrier_link_map: bool  # True when carrier_url col or dim_carriers view exists
