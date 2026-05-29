-- Monthly status snapshots for a customer (by customer_key). RETAIL-only mart, so
-- non-RETAIL customers legitimately return zero rows. Newest month last for charting.
SELECT
    snapshot_month,
    status,
    is_new,
    days_since_last_order,
    value_group
FROM mart_customer_status_snapshot_monthly
WHERE customer_key = ?
ORDER BY snapshot_month;
