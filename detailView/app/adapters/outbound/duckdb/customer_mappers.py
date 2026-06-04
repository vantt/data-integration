"""Map DuckDB row dicts -> customer domain dataclasses. Pure mapping, no duckdb import."""
from __future__ import annotations

from typing import Any

from app.domain.customer import (
    CustomerAction,
    CustomerBehavior,
    CustomerProfile,
    CustomerValueMetrics,
    OrderSummary,
    StatusSnapshot,
)

from . import row_coercion as rc

Row = dict[str, Any]


def map_profile(row: Row) -> CustomerProfile:
    return CustomerProfile(
        customer_id=rc.as_str(row.get("customer_id")) or "",
        full_name=rc.as_str(row.get("full_name")),
        phone=rc.as_str(row.get("phone")),
        email=rc.as_str(row.get("email")),
        dob=rc.as_date(row.get("dob")),  # dob is VARCHAR in dim_customers
        sex=rc.as_str(row.get("sex")),
        address1=rc.as_str(row.get("address1")),
        ward=rc.as_str(row.get("ward")),
        district=rc.as_str(row.get("district")),
        province=rc.as_str(row.get("province")),
        country=rc.as_str(row.get("country")),
        geo_region=rc.as_str(row.get("geo_region")),
        loyalty_point=rc.as_int(row.get("loyalty_point")),
        customer_type=rc.as_str(row.get("customer_type")),
        customer_group=rc.as_str(row.get("customer_group")),
        created_at=rc.as_datetime(row.get("created_at")),
        updated_at=rc.as_datetime(row.get("updated_at")),
    )


def map_behavior(row: Row) -> CustomerBehavior:
    return CustomerBehavior(
        recency_days=rc.as_int(row.get("recency_days")),
        frequency=rc.as_int(row.get("order_count")),
        monetary=rc.as_decimal(row.get("lifetime_value")),
        lifecycle_stage=rc.as_str(row.get("lifecycle_stage")),
        channel_preference=rc.as_str(row.get("channel_preference")),
        product_affinity=rc.as_str(row.get("product_affinity")),
        payment_behavior=rc.as_str(row.get("payment_behavior")),
        geo_region=rc.as_str(row.get("geo_region")),
        customer_type=rc.as_str(row.get("customer_type")),
        first_order_date=rc.as_datetime(row.get("first_order_date")),
        last_order_date=rc.as_datetime(row.get("last_order_date")),
        lifespan_days=rc.as_int(row.get("lifespan_days")),
    )


def map_value_metrics(profile_row: Row, agg_row: Row | None) -> CustomerValueMetrics:
    """LTV/tier from dim_customers; profit/cogs/returns aggregated over the order facts.

    Prefer the aggregated LTV/order-count (from the same fact scope as the other sums);
    fall back to the dim_customers pre-computed values when no aggregate rows exist.
    """
    agg = agg_row or {}
    lifetime_value = rc.as_decimal(agg.get("lifetime_value"))
    if lifetime_value is None:
        lifetime_value = rc.as_decimal(profile_row.get("lifetime_value"))
    total_orders = rc.as_int(agg.get("order_count"))
    if not total_orders:
        total_orders = rc.as_int(profile_row.get("order_count"))
    return CustomerValueMetrics(
        lifetime_value=lifetime_value,
        order_count=total_orders,
        value_group=rc.as_str(profile_row.get("value_group")),
        total_gross_profit=rc.as_decimal(agg.get("total_gross_profit")),
        total_cogs=rc.as_decimal(agg.get("total_cogs")),
        avg_gross_margin_pct=rc.as_float(agg.get("avg_gross_margin_pct")),
        total_return_amount=rc.as_decimal(agg.get("total_return_amount")),
        return_count=rc.as_int(agg.get("return_count")),
        cogs_order_count=rc.as_int(agg.get("cogs_order_count")),
    )


def map_status_snapshot(row: Row) -> StatusSnapshot:
    return StatusSnapshot(
        snapshot_month=rc.as_date(row.get("snapshot_month")),
        status=rc.as_str(row.get("status")),
        is_new=rc.as_bool(row.get("is_new")),
        days_since_last_order=rc.as_int(row.get("days_since_last_order")),
        value_group=rc.as_str(row.get("value_group")),
    )


def map_action(row: Row) -> CustomerAction:
    return CustomerAction(
        action_type=rc.as_str(row.get("action_type")) or "",
        priority_rank=rc.as_int(row.get("priority_rank")) or 9,
        action_rationale=rc.as_str(row.get("action_rationale")),
        value_at_stake=rc.as_decimal(row.get("value_at_stake")),
        avg_order_value=rc.as_decimal(row.get("avg_order_value")),
        avg_days_between_orders=rc.as_int(row.get("avg_days_between_orders")),
        next_purchase_signal=rc.as_str(row.get("next_purchase_signal")),
        discount_sensitivity=rc.as_str(row.get("discount_sensitivity")),
        predicted_next_purchase_date=rc.as_date(row.get("predicted_next_purchase_date")),
        cancel_rate=rc.as_float(row.get("cancel_rate")),
        recency_days=rc.as_int(row.get("recency_days")),
    )


def map_order_summary(row: Row) -> OrderSummary:
    return OrderSummary(
        order_code=rc.as_str(row.get("order_code")) or "",
        order_date=rc.as_datetime(row.get("order_date")),
        status=rc.as_str(row.get("status")),
        channel_name=rc.as_str(row.get("channel_name")),
        seller_name=rc.as_str(row.get("seller_name")),
        total_collected=rc.as_decimal(row.get("total_collected")),
        gross_profit=rc.as_decimal(row.get("gross_profit")),
        gross_margin_pct=rc.as_float(row.get("gross_margin_pct")),
        payment_label=rc.as_str(row.get("payment_label")),
        has_return=rc.as_bool(row.get("has_return")),
        carrier_id=rc.as_str(row.get("carrier_id")),
    )
