"""Build the standalone test DuckDB schema (DDL only).

Tables mirror the serving-layer column names/types the repositories query (verified
against the live information_schema). Only the columns the SQL touches are created —
DuckDB tolerates a narrower schema since queries reference columns by name.

Row seeding lives in ``tests/seed_rows.py`` to keep each module small and focused.
"""
from __future__ import annotations

import duckdb

from tests.seed_rows import seed_rows

# --- DDL: minimal column sets matching the serving views ----------------------------

_DDL = [
    """CREATE TABLE fact_orders (
        order_id VARCHAR, order_code VARCHAR, customer_key VARCHAR,
        shipping_geography_key VARCHAR, promotion_key VARCHAR, branch_location_key VARCHAR,
        channel_key VARCHAR, seller_staff_key VARCHAR, creator_staff_key VARCHAR,
        team_key VARCHAR, status VARCHAR, payment_status VARCHAR, fulfillment_status VARCHAR,
        gross_revenue DECIMAL(18,2), discount_amount DECIMAL(18,2), net_revenue DECIMAL(18,2),
        tax_amount DECIMAL(18,2), total_collected DECIMAL(18,2),
        first_shipped_at TIMESTAMPTZ, time_to_complete_hours BIGINT,
        max_discount_rate DOUBLE, primary_discount_nature VARCHAR, shipping_address VARCHAR,
        order_timestamp TIMESTAMPTZ, updated_at TIMESTAMPTZ )""",
    """CREATE TABLE fact_order_economics (
        order_id VARCHAR, order_code VARCHAR, cogs_amount DOUBLE, has_cogs BOOLEAN,
        gross_profit DECIMAL(38,2), gross_margin_pct DOUBLE,
        shopee_platform_fees BIGINT, shopee_infra_fee BIGINT, shopee_voucher_xtra_fee BIGINT,
        shopee_taxes BIGINT, shopee_net_settlement BIGINT, has_platform_fees BOOLEAN,
        channel_net_profit DECIMAL(38,2), channel_net_margin_pct DOUBLE,
        cod_amount DECIMAL(18,2), carrier_id VARCHAR,
        return_amount DECIMAL(38,2), return_count BIGINT, has_returns BOOLEAN )""",
    """CREATE TABLE fact_order_costs (
        order_id VARCHAR, order_code VARCHAR, cost_type VARCHAR, cost_category VARCHAR,
        amount DECIMAL(18,2), discount_rate DOUBLE, discount_nature VARCHAR,
        source_system VARCHAR, source_record VARCHAR, fee_source VARCHAR )""",
    """CREATE TABLE fact_order_returns (
        return_id VARCHAR, order_id BIGINT, order_code VARCHAR, return_date DATE,
        refund_amount DECIMAL(18,2), return_quantity INTEGER, return_status VARCHAR,
        refund_status VARCHAR, return_reason VARCHAR )""",
    """CREATE TABLE fact_payments (
        payment_key VARCHAR, order_id VARCHAR, payment_method_key VARCHAR,
        amount DECIMAL(18,2), status VARCHAR, payment_timestamp TIMESTAMPTZ, paid_on TIMESTAMPTZ )""",
    """CREATE TABLE fact_sales (
        product_key VARCHAR, order_id VARCHAR, item_id VARCHAR, quantity DECIMAL(18,2),
        revenue DECIMAL(18,2), discount_amount DECIMAL(18,2),
        distributed_discount_amount DECIMAL(18,2), weight_grams DECIMAL(18,2) )""",
    """CREATE TABLE fact_us_shipment_economics (
        order_id VARCHAR, order_code VARCHAR,
        total_us_revenue_excl_vat DECIMAL(38,4), total_us_revenue_incl_vat DECIMAL(38,4),
        line_item_count BIGINT, has_unpriced_sku BOOLEAN, unpriced_sku_count DOUBLE )""",
    """CREATE TABLE dim_customers (
        customer_key VARCHAR, customer_id VARCHAR, full_name VARCHAR, email VARCHAR,
        phone VARCHAR, dob VARCHAR, sex VARCHAR, address1 VARCHAR, ward VARCHAR,
        district VARCHAR, province VARCHAR, country VARCHAR, geo_region VARCHAR,
        loyalty_point INTEGER, customer_type VARCHAR, customer_group VARCHAR, value_group VARCHAR,
        lifecycle_stage VARCHAR, channel_preference VARCHAR, product_affinity VARCHAR,
        payment_behavior VARCHAR, lifetime_value DECIMAL(38,2), total_orders_count BIGINT,
        first_order_date TIMESTAMPTZ, last_order_date TIMESTAMPTZ, recency_days BIGINT,
        lifespan_days BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ )""",
    """CREATE TABLE dim_products (
        product_key VARCHAR, sku VARCHAR, product_name VARCHAR, variant_name VARCHAR,
        brand_name VARCHAR, category VARCHAR, unit VARCHAR )""",
    """CREATE TABLE dim_channels (
        channel_key VARCHAR, channel_name VARCHAR, channel_code VARCHAR,
        channel_category VARCHAR, channel_format VARCHAR, platform VARCHAR,
        channel_brand VARCHAR, market VARCHAR )""",
    """CREATE TABLE dim_staff ( staff_key VARCHAR, full_name VARCHAR, email VARCHAR )""",
    """CREATE TABLE dim_teams ( team_key VARCHAR, team_name VARCHAR )""",
    """CREATE TABLE dim_branch_location ( branch_location_key VARCHAR, branch_location_name VARCHAR )""",
    """CREATE TABLE dim_geography (
        geography_key VARCHAR, province VARCHAR, district VARCHAR, ward VARCHAR, country VARCHAR )""",
    """CREATE TABLE dim_promotions ( promotion_key VARCHAR, promotion_code VARCHAR )""",
    """CREATE TABLE dim_payment_methods (
        payment_method_key VARCHAR, payment_method_name VARCHAR, payment_method_type VARCHAR )""",
    """CREATE TABLE mart_customer_status_snapshot_monthly (
        customer_key VARCHAR, snapshot_month DATE, status VARCHAR, is_new BOOLEAN,
        days_since_last_order BIGINT, value_group VARCHAR )""",
]


def seed_database(con: duckdb.DuckDBPyConnection) -> None:
    """Create the tables, then insert the deterministic fixture rows."""
    for ddl in _DDL:
        con.execute(ddl)
    seed_rows(con)
