"""SQL constants for customer status timeline queries (mart_customer_status_snapshot_monthly)."""

TIMELINE_BY_CUSTOMER_KEY = """
SELECT
    snapshot_month,
    status,
    days_since_last_order,
    value_group,
    is_new
FROM main_marts.mart_customer_status_snapshot_monthly
WHERE customer_key = ?
ORDER BY snapshot_month ASC
LIMIT 24
"""

TIMELINE_BY_CUSTOMER_ID = """
SELECT
    m.snapshot_month,
    m.status,
    m.days_since_last_order,
    m.value_group,
    m.is_new
FROM main_marts.mart_customer_status_snapshot_monthly m
JOIN main_marts.dim_customers d ON d.customer_key = m.customer_key
WHERE d.customer_id = CAST(? AS VARCHAR)
ORDER BY m.snapshot_month ASC
LIMIT 24
"""
