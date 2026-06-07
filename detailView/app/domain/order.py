"""Order insight aggregate — the complete single-order view.

Field names mirror the OLAP serving views (see researcher-01 report) so the outbound
adapter maps 1:1. Money kept as Decimal | None; presentation/formatting lives in the web layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .shared import Badge, DataQualityFlag, Tone, safe_ratio

# Shipment status → badge tone mapping (used by the web template).
_SHIPMENT_TONE: dict[str, Tone] = {
    "DELIVERED": Tone.GOOD,
    "SHIPPING": Tone.WARN,
    "PACKED": Tone.NEUTRAL,
    "CANCELLED": Tone.BAD,
    "FAILED": Tone.BAD,
    "PENDING": Tone.WARN,
}


@dataclass
class Shipment:
    """Value object for one shipment leg (grain: 1 row per fact_fulfillments row)."""

    fulfillment_id: str | None = None
    fulfillment_code: str | None = None
    tracking_code: str | None = None
    carrier_id: str | None = None
    shipping_service: str | None = None
    status: str | None = None
    cod_amount: Decimal | None = None
    created_at: datetime | None = None
    shipped_at: datetime | None = None

    def status_tone(self) -> Tone:
        """Map shipment status to a badge tone for the UI layer."""
        if self.status is None:
            return Tone.NEUTRAL
        return _SHIPMENT_TONE.get(self.status.upper(), Tone.NEUTRAL)


@dataclass
class OrderHeader:
    order_code: str
    order_id: int | None = None
    status: str | None = None
    payment_status: str | None = None
    fulfillment_status: str | None = None
    created_at: datetime | None = None
    first_shipped_at: datetime | None = None
    updated_at: datetime | None = None
    time_to_complete_hours: int | None = None


@dataclass
class OrderFinancial:
    # Revenue waterfall (domestic)
    gross_revenue: Decimal | None = None
    discount_amount: Decimal | None = None
    net_revenue: Decimal | None = None
    vat_amount: Decimal | None = None
    total_collected: Decimal | None = None
    # Profit
    cogs_amount: Decimal | None = None
    gross_profit: Decimal | None = None
    gross_margin_pct: float | None = None
    channel_net_profit: Decimal | None = None
    channel_net_margin_pct: float | None = None
    # Shopee fee breakdown
    shopee_platform_fees: Decimal | None = None
    shopee_infra_fee: Decimal | None = None
    shopee_voucher_xtra_fee: Decimal | None = None
    shopee_taxes: Decimal | None = None
    shopee_net_settlement: Decimal | None = None
    # Logistics money
    cod_amount: Decimal | None = None
    carrier_id: str | None = None
    # Returns (reference only — NOT subtracted from this order's P&L)
    return_amount: Decimal | None = None
    return_count: int | None = None
    # Quality flags
    has_cogs: bool = False
    has_platform_fees: bool = False
    has_returns: bool = False
    # Phase-06: P&L tier-3 fields
    promo_goods_cost: Decimal | None = None
    cogs_source: str | None = None        # 'misa' | 'none' (extend when sapo_mac/both available)
    allocated_overhead: Decimal | None = None
    is_overhead_estimated: bool | None = None
    fully_loaded_net_profit: Decimal | None = None
    fully_loaded_margin_pct: float | None = None
    # US CrossBorder (fact_us_shipment_economics) — net_revenue=0 in fact_orders for US
    is_us: bool = False
    us_revenue_excl_vat: Decimal | None = None
    us_revenue_incl_vat: Decimal | None = None
    us_line_item_count: int | None = None
    has_unpriced_sku: bool = False
    unpriced_sku_count: int | None = None

    @property
    def effective_revenue(self) -> Decimal | None:
        """US orders report revenue from US shipment economics, not fact_orders.net_revenue."""
        if self.is_us:
            return self.us_revenue_incl_vat
        return self.total_collected if self.total_collected is not None else self.net_revenue

    @property
    def margin_is_verified(self) -> bool:
        if self.cogs_source is not None:
            return self.cogs_source in ('sapo_mac', 'both', 'misa')
        return self.has_cogs

    @property
    def shopee_platform_fee_rate(self) -> float | None:
        """Shopee platform fees as % of gross_revenue (always positive)."""
        if (self.shopee_platform_fees is None
                or self.gross_revenue is None
                or self.gross_revenue == 0):
            return None
        return float(abs(self.shopee_platform_fees) / self.gross_revenue)


@dataclass
class LineItem:
    order_line_id: int | None = None
    sku: str | None = None
    product_name: str | None = None
    variant_name: str | None = None
    brand_name: str | None = None
    category: str | None = None
    unit: str | None = None
    quantity: int | None = None
    revenue: Decimal | None = None
    discount_amount: Decimal | None = None
    distributed_discount_amount: Decimal | None = None
    weight_grams: Decimal | None = None
    # US line prices (only present for US CrossBorder orders, may be None)
    us_price_incl_vat: Decimal | None = None

    @property
    def unit_price(self) -> float | None:
        return safe_ratio(self.revenue, self.quantity)


@dataclass
class CostRow:
    cost_type: str | None = None
    cost_category: str | None = None  # COGS / PLATFORM_FEE / TAX / SHIPPING / DISCOUNT
    amount: Decimal | None = None
    discount_rate: Decimal | None = None
    discount_type: str | None = None
    source_system: str | None = None
    source_record: str | None = None
    fee_source: str | None = None  # actual / estimated


@dataclass
class CogsItem:
    """Per-SKU COGS line from int_order_cogs_reconciled. Grain: (order_code, sku)."""
    sku: str | None = None
    variant_id: int | None = None
    cogs_goods_sapo: Decimal | None = None   # Sapo-MAC primary
    cogs_goods_misa: Decimal | None = None   # MISA TK632 cross-check (None if absent)
    cogs_goods_primary: Decimal | None = None  # value used in P&L
    cogs_source: str | None = None           # sapo_mac | both | misa | none
    qty_sapo: float | None = None
    is_promo: bool = False                   # gift line (line_revenue = 0)
    is_gift_no_invoice: bool | None = None   # Sapo has cost, MISA has no entry at all


@dataclass
class Payment:
    payment_method_name: str | None = None
    payment_method_type: str | None = None
    amount: Decimal | None = None
    status: str | None = None
    payment_timestamp: datetime | None = None
    paid_on: datetime | None = None


@dataclass
class ReturnEvent:
    return_date: datetime | None = None
    refund_amount: Decimal | None = None
    return_quantity: int | None = None
    return_status: str | None = None
    refund_status: str | None = None
    return_reason: str | None = None


@dataclass
class ChannelInfo:
    channel_name: str | None = None
    channel_code: str | None = None
    channel_category: str | None = None
    channel_format: str | None = None
    platform: str | None = None
    channel_brand: str | None = None
    market: str | None = None  # Domestic / Export
    promotion_code: str | None = None
    max_discount_rate: Decimal | None = None
    primary_discount_type: str | None = None


@dataclass
class StaffInfo:
    seller_name: str | None = None
    seller_email: str | None = None
    creator_name: str | None = None
    team_name: str | None = None
    branch_name: str | None = None


@dataclass
class ShippingInfo:
    province: str | None = None
    district: str | None = None
    ward: str | None = None
    country: str | None = None
    address: str | None = None


@dataclass
class CustomerRef:
    customer_id: str | None = None
    full_name: str | None = None
    customer_type: str | None = None
    value_group: str | None = None
    lifetime_value: Decimal | None = None
    # Outreach action from mart_customer_action_queue (optional — degrades gracefully)
    customer_action_type: str | None = None
    customer_action_rationale: str | None = None


@dataclass
class OrderDetail:
    header: OrderHeader
    financial: OrderFinancial = field(default_factory=OrderFinancial)
    line_items: list[LineItem] = field(default_factory=list)
    cost_ledger: list[CostRow] = field(default_factory=list)
    cogs_items: list[CogsItem] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    returns: list[ReturnEvent] = field(default_factory=list)
    shipments: list[Shipment] = field(default_factory=list)
    channel: ChannelInfo = field(default_factory=ChannelInfo)
    staff: StaffInfo = field(default_factory=StaffInfo)
    shipping: ShippingInfo = field(default_factory=ShippingInfo)
    customer: CustomerRef = field(default_factory=CustomerRef)

    def status_badges(self) -> list[Badge]:
        out: list[Badge] = []
        tone_map = {
            "COMPLETED": Tone.GOOD, "PAID": Tone.GOOD,
            "CANCELLED": Tone.BAD, "VOIDED": Tone.BAD, "REFUNDED": Tone.WARN,
            "PARTIALLY_PAID": Tone.WARN, "PENDING": Tone.WARN, "UNPAID": Tone.WARN,
        }
        for kind, value in (
            ("status", self.header.status),
            ("payment", self.header.payment_status),
            ("fulfillment", self.header.fulfillment_status),
        ):
            if value:
                out.append(Badge(value, tone_map.get(value, Tone.NEUTRAL), kind))
        return out

    def quality_flags(self, cap=None) -> list[DataQualityFlag]:
        """Compute per-order data-quality flags.

        Args:
            cap: Optional CapabilityPort. When provided, enables self-healing flags
                 that auto-silence when the pipeline adds the relevant schema objects.
                 Pass None for backward compatibility (all self-healing flags shown).
        """
        flags: list[DataQualityFlag] = []
        if self.financial.is_us:
            flags.append(DataQualityFlag("is_us", "US CrossBorder revenue", "info"))
            if self.financial.has_unpriced_sku:
                flags.append(DataQualityFlag("unpriced_sku", "Some SKUs missing US price", "warn"))
        if self.financial.cogs_source in (None, 'none'):
            flags.append(DataQualityFlag("no_cogs", "Margin unverified — no COGS match for this order", "warn"))
        if self.financial.has_returns:
            flags.append(DataQualityFlag("has_returns", "Has returns (reference only in P&L)", "info"))
        if not self.financial.has_platform_fees and (self.financial.shopee_platform_fees is None):
            flags.append(DataQualityFlag("no_platform_fees", "No platform-fee data", "info"))
        # Self-healing carrier-link flag: silences automatically when the pipeline adds
        # a carrier_url column to fact_fulfillments OR creates a dim_carriers view.
        if cap is None or (
            not cap.has_column("fact_fulfillments", "carrier_url")
            and not cap.view_exists("dim_carriers")
        ):
            flags.append(DataQualityFlag(
                "no_carrier_link",
                "Tracking codes are copy-only — no carrier URL map",
                "info",
            ))
        return flags
