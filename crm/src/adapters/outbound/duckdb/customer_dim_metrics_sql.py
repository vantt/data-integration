"""SQL constants for customer dim_customers segments + aggregated value metrics."""

# Single query — replaces the old two-step DIM_BY_CUSTOMER_ID + VALUE_METRICS_BY_CUSTOMER_KEY
# round-trip pair. Both column sets live on dim_customers so one lookup suffices.
METRICS_BY_CUSTOMER_ID = """
SELECT
    customer_key,
    lifecycle_stage,
    product_affinity,
    payment_behavior,
    geo_region,
    customer_type,
    first_order_date,
    lifetime_gross_profit   AS total_gross_profit,
    total_cogs,
    avg_gross_margin_pct,
    total_return_amount,
    return_count,
    cogs_order_count,
    order_count
FROM main_marts.dim_customers
WHERE customer_id = CAST(? AS VARCHAR)
LIMIT 1
"""
