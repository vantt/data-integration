"""Row-dict → domain entity mappers for the CRM order header row.

Covers the single wide header row returned by HEADER_SQL (fact_orders joined to
all dimension tables). Collection-row mappers live in order_collection_mappers.py.

None-safe: missing keys default to '' / 0 / False / None per field type.
"""
from __future__ import annotations

from domain.entities.order import (
    ChannelInfo,
    CustomerRef,
    OrderFinancial,
    OrderHeader,
    ShippingInfo,
    StaffInfo,
)

# ── shared scalar helpers (re-exported for order_collection_mappers) ──────────

def _s(row: dict, key: str) -> str:
    """Nullable string — returns '' when None."""
    v = row.get(key)
    return v if isinstance(v, str) else (str(v) if v is not None else "")


def _i(row: dict, key: str) -> int:
    """Nullable DECIMAL/float → rounded int (VND monetary amounts)."""
    v = row.get(key)
    if v is None:
        return 0
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


def _f(row: dict, key: str) -> float | None:
    """Nullable float — returns None when absent (percentage fields)."""
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _b(row: dict, key: str) -> bool:
    """Nullable bool — returns False when absent."""
    v = row.get(key)
    return bool(v) if v is not None else False


# ── header-row mappers ────────────────────────────────────────────────────────

def map_header(row: dict) -> OrderHeader:
    return OrderHeader(
        order_code=_s(row, "order_code"),
        order_id=_s(row, "order_id"),
        status=_s(row, "status"),
        payment_status=_s(row, "payment_status"),
        fulfillment_status=_s(row, "fulfillment_status"),
        created_at=_s(row, "created_at"),
        first_shipped_at=_s(row, "first_shipped_at"),
        updated_at=_s(row, "updated_at"),
        time_to_complete_hours=_f(row, "time_to_complete_hours"),
        date_actual=_s(row, "date_actual"),
        year=int(row.get("year") or 0),
        month=int(row.get("month") or 0),
        quarter=int(row.get("quarter") or 0),
        day_of_week=int(row.get("day_of_week") or 0),
        is_weekend=_b(row, "is_weekend"),
        time_of_day_24=_s(row, "time_of_day_24"),
        day_period=_s(row, "day_period"),
        is_business_hour=_b(row, "is_business_hour"),
        is_peak_hour=_b(row, "is_peak_hour"),
    )


def map_financial(row: dict) -> OrderFinancial:
    return OrderFinancial(
        gross_revenue=_i(row, "gross_revenue"),
        discount_amount=_i(row, "discount_amount"),
        net_revenue=_i(row, "net_revenue"),
        vat_amount=_i(row, "vat_amount"),
        total_collected=_i(row, "total_collected"),
        cogs_amount=_i(row, "cogs_amount"),
        gross_profit=_i(row, "gross_profit"),
        gross_margin_pct=_f(row, "gross_margin_pct"),
        channel_net_profit=_i(row, "channel_net_profit"),
        channel_net_margin_pct=_f(row, "channel_net_margin_pct"),
        shopee_platform_fees=_i(row, "shopee_platform_fees"),
        shopee_infra_fee=_i(row, "shopee_infra_fee"),
        shopee_voucher_xtra_fee=_i(row, "shopee_voucher_xtra_fee"),
        shopee_taxes=_i(row, "shopee_taxes"),
        shopee_net_settlement=_i(row, "shopee_net_settlement"),
        cod_amount=_i(row, "cod_amount"),
        carrier_id=_s(row, "carrier_id"),
        return_amount=_i(row, "return_amount"),
        return_count=int(row.get("return_count") or 0),
        has_cogs=_b(row, "has_cogs"),
        has_platform_fees=_b(row, "has_platform_fees"),
        has_returns=_b(row, "has_returns"),
        promo_goods_cost=_i(row, "promo_goods_cost"),
        cogs_source=_s(row, "cogs_source"),
        allocated_overhead=_i(row, "allocated_overhead"),
        is_overhead_estimated=_b(row, "is_overhead_estimated"),
        fully_loaded_net_profit=_i(row, "fully_loaded_net_profit"),
        fully_loaded_margin_pct=_f(row, "fully_loaded_margin_pct"),
        is_us=_b(row, "is_us"),
        us_revenue_excl_vat=_i(row, "total_us_revenue_excl_vat"),
        us_revenue_incl_vat=_i(row, "total_us_revenue_incl_vat"),
        us_line_item_count=int(row.get("us_line_item_count") or 0),
        has_unpriced_sku=_b(row, "has_unpriced_sku"),
        unpriced_sku_count=int(row.get("unpriced_sku_count") or 0),
    )


def map_channel(row: dict) -> ChannelInfo:
    return ChannelInfo(
        channel_name=_s(row, "channel_name"),
        channel_code=_s(row, "channel_code"),
        channel_category=_s(row, "channel_category"),
        channel_format=_s(row, "channel_format"),
        platform=_s(row, "platform"),
        channel_brand=_s(row, "channel_brand"),
        market=_s(row, "market"),
        promotion_code=_s(row, "promotion_code"),
        primary_discount_type=_s(row, "primary_discount_type"),
        max_discount_rate=_f(row, "max_discount_rate"),
    )


def map_staff(row: dict) -> StaffInfo:
    return StaffInfo(
        seller_name=_s(row, "seller_name"),
        seller_email=_s(row, "seller_email"),
        creator_name=_s(row, "creator_name"),
        team_name=_s(row, "team_name"),
        branch_name=_s(row, "branch_name"),
    )


def map_shipping(row: dict) -> ShippingInfo:
    return ShippingInfo(
        province=_s(row, "province"),
        district=_s(row, "district"),
        ward=_s(row, "ward"),
        country=_s(row, "country"),
        address=_s(row, "shipping_address"),
    )


def map_customer(row: dict) -> CustomerRef | None:
    """Returns None when no customer_key is linked to the order."""
    cust_id_raw = row.get("cust_customer_id")
    if not cust_id_raw:
        return None
    return CustomerRef(
        customer_id=str(cust_id_raw),
        full_name=_s(row, "cust_full_name"),
        customer_type=_s(row, "cust_customer_type"),
        value_group=_s(row, "cust_value_group"),
        lifetime_value=_i(row, "cust_lifetime_value"),
        customer_action_type="",
        customer_action_rationale="",
    )
