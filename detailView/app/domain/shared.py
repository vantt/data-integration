"""Shared value objects, enums, and small helpers used across the domain."""
from __future__ import annotations

from dataclasses import dataclass, field
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


class OrderTab(str, Enum):
    FINANCIAL = "financial"
    LINE_ITEMS = "line-items"
    COST_LEDGER = "cost-ledger"
    PAYMENTS = "payments"
    FULFILLMENT = "fulfillment"
    RETURNS = "returns"
    CHANNEL_STAFF = "channel-staff"
    TIMELINE = "timeline"


class CustomerTab(str, Enum):
    VALUE_METRICS = "value-metrics"
    BEHAVIOR = "behavior"
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
