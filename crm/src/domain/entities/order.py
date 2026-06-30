"""CRM Order domain entities — read-only aggregate from olap.duckdb serving layer.

CRM reads from fact_orders + fact_order_economics + dimension tables via DuckDB adapter.
Python never writes here. Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

COGS_VARIANCE_WARN_PCT: float = 10.0  # >10 % variance = high

# ---------------------------------------------------------------------------
# Entities — header / financial split for clarity and line-limit compliance
# ---------------------------------------------------------------------------

@dataclass
class OrderHeader:
    """Per-order identity and lifecycle timestamps."""
    order_code: str
    order_id: str
    status: str
    payment_status: str
    fulfillment_status: str
    created_at: str             # UTC ISO-8601
    first_shipped_at: str       # UTC ISO-8601; empty when not yet shipped
    updated_at: str             # UTC ISO-8601
    time_to_complete_hours: Optional[float] = None  # None when order not yet complete
    # dim_date / dim_time attributes (joined via fo.date_key / fo.time_key)
    date_actual: str = ""       # YYYY-MM-DD (ICT date of order)
    year: int = 0
    month: int = 0
    quarter: int = 0
    day_of_week: int = 0        # 0=Sunday … 6=Saturday (DuckDB extract(dayofweek))
    is_weekend: bool = False
    time_of_day_24: str = ""    # HH:MM (ICT time of order)
    day_period: str = ""        # Morning | Afternoon | Evening | Night
    is_business_hour: bool = False
    is_peak_hour: bool = False


@dataclass
class OrderFinancial:
    """Revenue waterfall + P&L economics for one order.

    All *_vnd / gross_* / net_* amounts are int (rounded from warehouse DECIMAL).
    Pct fields are Optional[float] — None means not applicable (e.g. zero revenue).
    """
    # Revenue waterfall (fact_orders)
    gross_revenue: int
    discount_amount: int
    net_revenue: int
    vat_amount: int
    total_collected: int
    # P&L economics (fact_order_economics — LEFT JOIN, all may be zero)
    cogs_amount: int = 0
    gross_profit: int = 0
    gross_margin_pct: Optional[float] = None
    channel_net_profit: int = 0
    channel_net_margin_pct: Optional[float] = None
    shopee_platform_fees: int = 0
    shopee_infra_fee: int = 0
    shopee_voucher_xtra_fee: int = 0
    shopee_taxes: int = 0
    shopee_net_settlement: int = 0
    cod_amount: int = 0
    carrier_id: str = ""
    return_amount: int = 0
    return_count: int = 0
    has_cogs: bool = False
    has_platform_fees: bool = False
    has_returns: bool = False
    # Phase-06 fully-loaded fields
    promo_goods_cost: int = 0
    cogs_source: str = ""       # sapo_mac|misa|both|none
    allocated_overhead: int = 0
    is_overhead_estimated: bool = False
    fully_loaded_net_profit: int = 0
    fully_loaded_margin_pct: Optional[float] = None
    # US CrossBorder (fact_us_shipment_economics — LEFT JOIN)
    is_us: bool = False
    us_revenue_excl_vat: int = 0
    us_revenue_incl_vat: int = 0
    us_line_item_count: int = 0
    has_unpriced_sku: bool = False
    unpriced_sku_count: int = 0

    @property
    def cogs_pct_of_net(self) -> Optional[float]:
        if not self.net_revenue or self.net_revenue <= 0:
            return None
        return self.cogs_amount / self.net_revenue

    @property
    def discount_rate(self) -> Optional[float]:
        if not self.gross_revenue or not self.discount_amount:
            return None
        return self.discount_amount / self.gross_revenue

    @property
    def cogs_source_label(self) -> str:
        if not self.cogs_source or self.cogs_source == "none":
            return "unverified"
        if self.cogs_source in ("sapo_mac", "both"):
            return "Sapo-MAC"
        return ""

    def composition_segments(self) -> Optional[dict]:
        """Normalized COGS/fees/profit proportions for revenue composition bar.

        Returns {cogs_pct, fees_pct, profit_pct} that roughly sum to 100,
        or None when unavailable (US order, zero revenue, or no COGS).
        """
        if self.is_us or not self.net_revenue or self.net_revenue <= 0 or not self.cogs_amount:
            return None
        fees_val = abs(self.shopee_platform_fees) if self.has_platform_fees and self.shopee_platform_fees else 0
        profit_val = max(self.gross_profit, 0)
        cogs_raw = max(self.cogs_amount / self.net_revenue * 100, 0.0)
        fees_raw = max(fees_val / self.net_revenue * 100, 0.0)
        profit_raw = max(profit_val / self.net_revenue * 100, 0.0)
        total = cogs_raw + fees_raw + profit_raw
        if not total:
            return None
        def _p(raw: float) -> float:
            return min(round(raw / total * 100, 1), 100.0)
        cogs_pct = _p(cogs_raw)
        return {"cogs_pct": cogs_pct, "fees_pct": _p(fees_raw), "profit_pct": _p(profit_raw)} if cogs_pct > 0 else None


@dataclass
class OrderLineItem:
    """One fact_sales row joined to dim_products."""
    order_line_id: str
    sku: str
    product_name: str
    variant_name: str
    brand_name: str
    category: str
    unit: str
    quantity: int
    revenue: int
    discount_amount: int
    distributed_discount_amount: int
    weight_grams: Optional[int] = None


@dataclass
class Shipment:
    """One fact_fulfillments row."""
    fulfillment_id: str
    fulfillment_code: str
    tracking_code: str
    carrier_id: str
    shipping_service: str
    status: str
    cod_amount: int
    created_at: str     # UTC ISO
    shipped_at: str     # UTC ISO; empty if not shipped

    _STAGE_ORDER = ("PACKED", "SHIPPING", "DELIVERED")

    @property
    def progress_stage_index(self) -> int:
        """Index in PACKED→SHIPPING→DELIVERED progression. -1 when status is bad/unknown."""
        try:
            return list(self._STAGE_ORDER).index((self.status or "").upper())
        except ValueError:
            return -1


@dataclass
class CostRow:
    """One fact_order_costs row (cost ledger)."""
    cost_type: str
    cost_category: str
    amount: int
    discount_type: str
    source_system: str
    source_record: str
    fee_source: str
    discount_rate: Optional[float] = None


@dataclass
class CogsItem:
    """One int_order_cogs_reconciled row (per-SKU COGS breakdown)."""
    sku: str
    variant_id: str
    cogs_goods_sapo: int
    cogs_goods_misa: int
    cogs_goods_primary: int
    cogs_source: str
    qty_sapo: float
    is_promo: bool
    is_gift_no_invoice: bool

    @property
    def variance(self) -> Optional[int]:
        if self.cogs_goods_sapo is None or self.cogs_goods_misa is None:
            return None
        return self.cogs_goods_sapo - self.cogs_goods_misa

    @property
    def variance_pct(self) -> Optional[float]:
        v = self.variance
        if v is None or not self.cogs_goods_misa:
            return None
        return v / self.cogs_goods_misa * 100

    @property
    def is_high_variance(self) -> bool:
        v = self.variance_pct
        return v is not None and abs(v) > COGS_VARIANCE_WARN_PCT


@dataclass
class Payment:
    """One fact_payments row joined to dim_payment_methods."""
    payment_method_name: str
    payment_method_type: str
    amount: int
    status: str
    payment_timestamp: str  # UTC ISO; empty when absent
    paid_on: str            # YYYY-MM-DD; empty when absent


@dataclass
class ReturnEvent:
    """One fact_order_returns row."""
    return_date: str        # YYYY-MM-DD
    refund_amount: int
    return_quantity: int
    return_status: str
    refund_status: str
    return_reason: str


@dataclass
class ChannelInfo:
    """Dimension data from dim_channels + dim_promotions."""
    channel_name: str
    channel_code: str
    channel_category: str
    channel_format: str
    platform: str
    channel_brand: str
    market: str
    promotion_code: str
    primary_discount_type: str
    max_discount_rate: Optional[float] = None


@dataclass
class StaffInfo:
    """Dimension data from dim_staff + dim_teams + dim_branch_location."""
    seller_name: str
    seller_email: str
    creator_name: str
    team_name: str
    branch_name: str


@dataclass
class ShippingInfo:
    """Dimension data from dim_geography + fact_orders.shipping_address."""
    province: str
    district: str
    ward: str
    country: str
    address: str


@dataclass
class CustomerRef:
    """Linked customer from dim_customers; None on OrderDetail when no customer_key."""
    customer_id: str            # Sapo customer_id (VARCHAR in serving layer)
    full_name: str
    customer_type: str
    value_group: str
    lifetime_value: int
    customer_action_type: str       # from mart_customer_action_queue; empty when absent
    customer_action_rationale: str


@dataclass
class OrderDetail:
    """Full single-order aggregate read from olap.duckdb."""
    header: OrderHeader
    financial: OrderFinancial
    channel: ChannelInfo
    staff: StaffInfo
    shipping: ShippingInfo
    line_items: list[OrderLineItem] = field(default_factory=list)
    cost_ledger: list[CostRow] = field(default_factory=list)
    cogs_items: list[CogsItem] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    returns: list[ReturnEvent] = field(default_factory=list)
    shipments: list[Shipment] = field(default_factory=list)

    @property
    def cogs_reconciliation_totals(self) -> Optional[dict]:
        """Pre-aggregated Sapo/MISA totals for the COGS reconciliation footer.

        Returns None when items don't have both sources.
        """
        sapo_vals = [i.cogs_goods_sapo for i in self.cogs_items if i.cogs_goods_sapo is not None]
        misa_vals = [i.cogs_goods_misa for i in self.cogs_items if i.cogs_goods_misa is not None]
        if not sapo_vals or not misa_vals:
            return None
        sapo_total = sum(sapo_vals)
        misa_total = sum(misa_vals)
        variance = sapo_total - misa_total
        variance_pct = variance / misa_total * 100 if misa_total else None
        return {
            "sapo_total": sapo_total,
            "misa_total": misa_total,
            "variance": variance,
            "variance_pct": variance_pct,
            "is_high_variance": variance_pct is not None and abs(variance_pct) > COGS_VARIANCE_WARN_PCT,
        }

    @property
    def shipment_status_summary(self) -> dict:
        """Count of shipments per status for the summary strip."""
        counts: dict[str, int] = {}
        for s in self.shipments:
            key = (s.status or "").lower()
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def payment_cod_summary(self) -> dict:
        """Total payment amount and COD amount + percentage for the payments footer."""
        total = sum(p.amount for p in self.payments)
        cod = sum(p.amount for p in self.payments if (p.payment_method_type or "").upper() == "COD")
        cod_pct = int(cod / total * 100) if total else 0
        return {"total": total, "cod": cod, "cod_pct": cod_pct}

    customer: Optional[CustomerRef] = None  # None when order has no linked customer
