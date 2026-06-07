"""Map DuckDB row dicts -> order domain dataclasses. No duckdb import: pure mapping.

Each function takes already-fetched column-keyed dicts (see fetch_helpers) and returns
domain objects. The header row drives OrderHeader/OrderFinancial/Channel/Staff/Shipping/
CustomerRef; collection rows drive line items, costs, payments, returns.
"""
from __future__ import annotations

from typing import Any

from app.domain.order import (
    ChannelInfo,
    CogsItem,
    CostRow,
    CustomerRef,
    LineItem,
    OrderFinancial,
    OrderHeader,
    Payment,
    ReturnEvent,
    Shipment,
    ShippingInfo,
    StaffInfo,
)

from . import row_coercion as rc

Row = dict[str, Any]


def map_header(row: Row) -> OrderHeader:
    return OrderHeader(
        order_code=rc.as_str(row.get("order_code")) or "",
        order_id=rc.as_int(row.get("order_id")),
        status=rc.as_str(row.get("status")),
        payment_status=rc.as_str(row.get("payment_status")),
        fulfillment_status=rc.as_str(row.get("fulfillment_status")),
        created_at=rc.as_datetime(row.get("created_at")),
        first_shipped_at=rc.as_datetime(row.get("first_shipped_at")),
        updated_at=rc.as_datetime(row.get("updated_at")),
        time_to_complete_hours=rc.as_int(row.get("time_to_complete_hours")),
    )


def map_financial(row: Row) -> OrderFinancial:
    is_us = rc.as_bool(row.get("is_us"))
    return OrderFinancial(
        gross_revenue=rc.as_decimal(row.get("gross_revenue")),
        discount_amount=rc.as_decimal(row.get("discount_amount")),
        net_revenue=rc.as_decimal(row.get("net_revenue")),
        vat_amount=rc.as_decimal(row.get("vat_amount")),
        total_collected=rc.as_decimal(row.get("total_collected")),
        cogs_amount=rc.as_decimal(row.get("cogs_amount")),
        gross_profit=rc.as_decimal(row.get("gross_profit")),
        gross_margin_pct=rc.as_float(row.get("gross_margin_pct")),
        channel_net_profit=rc.as_decimal(row.get("channel_net_profit")),
        channel_net_margin_pct=rc.as_float(row.get("channel_net_margin_pct")),
        shopee_platform_fees=rc.as_decimal(row.get("shopee_platform_fees")),
        shopee_infra_fee=rc.as_decimal(row.get("shopee_infra_fee")),
        shopee_voucher_xtra_fee=rc.as_decimal(row.get("shopee_voucher_xtra_fee")),
        shopee_taxes=rc.as_decimal(row.get("shopee_taxes")),
        shopee_net_settlement=rc.as_decimal(row.get("shopee_net_settlement")),
        cod_amount=rc.as_decimal(row.get("cod_amount")),
        carrier_id=rc.as_str(row.get("carrier_id")),
        return_amount=rc.as_decimal(row.get("return_amount")),
        return_count=rc.as_int(row.get("return_count")),
        has_cogs=rc.as_bool(row.get("has_cogs")),
        has_platform_fees=rc.as_bool(row.get("has_platform_fees")),
        has_returns=rc.as_bool(row.get("has_returns")),
        promo_goods_cost=rc.as_decimal(row.get("promo_goods_cost")),
        cogs_source=rc.as_str(row.get("cogs_source")),
        allocated_overhead=rc.as_decimal(row.get("allocated_overhead")),
        is_overhead_estimated=rc.as_bool(row.get("is_overhead_estimated")),
        fully_loaded_net_profit=rc.as_decimal(row.get("fully_loaded_net_profit")),
        fully_loaded_margin_pct=rc.as_float(row.get("fully_loaded_margin_pct")),
        # US CrossBorder — net_revenue is 0 in fact_orders for US orders.
        is_us=is_us,
        us_revenue_excl_vat=rc.as_decimal(row.get("total_us_revenue_excl_vat")),
        us_revenue_incl_vat=rc.as_decimal(row.get("total_us_revenue_incl_vat")),
        us_line_item_count=rc.as_int(row.get("us_line_item_count")),
        has_unpriced_sku=rc.as_bool(row.get("has_unpriced_sku")),
        unpriced_sku_count=rc.as_int(row.get("unpriced_sku_count")),
    )


def map_channel(row: Row) -> ChannelInfo:
    return ChannelInfo(
        channel_name=rc.as_str(row.get("channel_name")),
        channel_code=rc.as_str(row.get("channel_code")),
        channel_category=rc.as_str(row.get("channel_category")),
        channel_format=rc.as_str(row.get("channel_format")),
        platform=rc.as_str(row.get("platform")),
        channel_brand=rc.as_str(row.get("channel_brand")),
        market=rc.as_str(row.get("market")),
        promotion_code=rc.as_str(row.get("promotion_code")),
        max_discount_rate=rc.as_decimal(row.get("max_discount_rate")),
        primary_discount_type=rc.as_str(row.get("primary_discount_type")),
    )


def map_staff(row: Row) -> StaffInfo:
    return StaffInfo(
        seller_name=rc.as_str(row.get("seller_name")),
        seller_email=rc.as_str(row.get("seller_email")),
        creator_name=rc.as_str(row.get("creator_name")),
        team_name=rc.as_str(row.get("team_name")),
        branch_name=rc.as_str(row.get("branch_name")),
    )


def map_shipping(row: Row) -> ShippingInfo:
    return ShippingInfo(
        province=rc.as_str(row.get("province")),
        district=rc.as_str(row.get("district")),
        ward=rc.as_str(row.get("ward")),
        country=rc.as_str(row.get("country")),
        address=rc.as_str(row.get("shipping_address")),
    )


def map_customer_ref(row: Row) -> CustomerRef:
    return CustomerRef(
        customer_id=rc.as_str(row.get("cust_customer_id")),
        full_name=rc.as_str(row.get("cust_full_name")),
        customer_type=rc.as_str(row.get("cust_customer_type")),
        value_group=rc.as_str(row.get("cust_value_group")),
        lifetime_value=rc.as_decimal(row.get("cust_lifetime_value")),
    )


def map_line_item(row: Row) -> LineItem:
    return LineItem(
        order_line_id=rc.as_int(row.get("order_line_id")),
        sku=rc.as_str(row.get("sku")),
        product_name=rc.as_str(row.get("product_name")),
        variant_name=rc.as_str(row.get("variant_name")),
        brand_name=rc.as_str(row.get("brand_name")),
        category=rc.as_str(row.get("category")),
        unit=rc.as_str(row.get("unit")),
        quantity=rc.as_int(row.get("quantity")),
        revenue=rc.as_decimal(row.get("revenue")),
        discount_amount=rc.as_decimal(row.get("discount_amount")),
        distributed_discount_amount=rc.as_decimal(row.get("distributed_discount_amount")),
        weight_grams=rc.as_decimal(row.get("weight_grams")),
        us_price_incl_vat=None,  # int_* line-price model is out of read-only scope
    )


def map_cost_row(row: Row) -> CostRow:
    return CostRow(
        cost_type=rc.as_str(row.get("cost_type")),
        cost_category=rc.as_str(row.get("cost_category")),
        amount=rc.as_decimal(row.get("amount")),
        discount_rate=rc.as_decimal(row.get("discount_rate")),
        discount_type=rc.as_str(row.get("discount_type")),
        source_system=rc.as_str(row.get("source_system")),
        source_record=rc.as_str(row.get("source_record")),
        fee_source=rc.as_str(row.get("fee_source")),
    )


def map_cogs_item(row: Row) -> CogsItem:
    return CogsItem(
        sku=rc.as_str(row.get("sku")),
        variant_id=rc.as_int(row.get("variant_id")),
        cogs_goods_sapo=rc.as_decimal(row.get("cogs_goods_sapo")),
        cogs_goods_misa=rc.as_decimal(row.get("cogs_goods_misa")),
        cogs_goods_primary=rc.as_decimal(row.get("cogs_goods_primary")),
        cogs_source=rc.as_str(row.get("cogs_source")),
        qty_sapo=rc.as_float(row.get("qty_sapo")),
        is_promo=rc.as_bool(row.get("is_promo")) or False,
        is_gift_no_invoice=rc.as_bool(row.get("is_gift_no_invoice")),
    )


def map_payment(row: Row) -> Payment:
    return Payment(
        payment_method_name=rc.as_str(row.get("payment_method_name")),
        payment_method_type=rc.as_str(row.get("payment_method_type")),
        amount=rc.as_decimal(row.get("amount")),
        status=rc.as_str(row.get("status")),
        payment_timestamp=rc.as_datetime(row.get("payment_timestamp")),
        paid_on=rc.as_datetime(row.get("paid_on")),
    )


def map_return_event(row: Row) -> ReturnEvent:
    return ReturnEvent(
        return_date=_as_dt_or_none(row.get("return_date")),
        refund_amount=rc.as_decimal(row.get("refund_amount")),
        return_quantity=rc.as_int(row.get("return_quantity")),
        return_status=rc.as_str(row.get("return_status")),
        refund_status=rc.as_str(row.get("refund_status")),
        return_reason=rc.as_str(row.get("return_reason")),
    )


def map_shipment(row: Row) -> Shipment:
    """Map one fact_fulfillments row to a Shipment value object."""
    return Shipment(
        fulfillment_id=rc.as_str(row.get("fulfillment_id")),
        fulfillment_code=rc.as_str(row.get("fulfillment_code")),
        tracking_code=rc.as_str(row.get("tracking_code")),
        carrier_id=rc.as_str(row.get("carrier_id")),
        shipping_service=rc.as_str(row.get("shipping_service")),
        status=rc.as_str(row.get("status")),
        cod_amount=rc.as_decimal(row.get("cod_amount")),
        created_at=rc.as_datetime(row.get("created_at")),
        shipped_at=rc.as_datetime(row.get("shipped_at")),
    )


def _as_dt_or_none(value: Any):
    """return_date is a DATE; ReturnEvent.return_date is datetime|None. Promote date->datetime."""
    from datetime import date, datetime

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return None
