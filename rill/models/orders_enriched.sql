WITH base AS (
    SELECT
        o.order_id,
        o.order_code,
        o.order_timestamp,
        date_trunc('day', o.order_timestamp) AS order_date,
        date_trunc('hour', o.order_timestamp) AS hour_start,
        EXTRACT(HOUR FROM o.order_timestamp) AS order_hour,
        strftime(o.order_timestamp, '%a') AS day_of_week,
        c.channel_name,
        c.channel_code,
        c.channel_category,
        c.platform_group,
        c.platform,
        c.channel_brand,
        c.market,
        c.customer_segment,
        COALESCE(c.is_sales_channel, false) AS is_sales_channel,
        b.branch_location_name,
        b.branch_location_code,
        g.province,
        g.district,
        g.ward,
        g.country,
        s.full_name AS staff_name,
        s.email AS staff_email,
        o.status,
        o.payment_status,
        o.fulfillment_status,
        o.gross_revenue,
        o.discount_amount,
        o.net_revenue,
        o.tax_amount,
        o.total_collected,
        o.first_shipped_at,
        o.time_to_complete_hours AS hours_to_complete,
        CASE
            WHEN o.first_shipped_at IS NULL THEN NULL
            ELSE date_diff('hour', o.order_timestamp, o.first_shipped_at)
        END AS hours_to_first_ship
    FROM src_fact_orders o
    LEFT JOIN src_dim_channels c ON o.channel_key = c.channel_key
    LEFT JOIN src_dim_branch_location b ON o.branch_location_key = b.branch_location_key
    LEFT JOIN src_dim_geography g ON o.shipping_geography_key = g.geography_key
    LEFT JOIN src_dim_staff s ON o.staff_key = s.staff_key
),
flags AS (
    SELECT
        *,
        status = 'COMPLETED' AS is_completed,
        status = 'CANCELLED' AS is_cancelled,
        status = 'OPEN' AS is_open,
        lower(COALESCE(fulfillment_status, '')) = 'fulfilled' AS is_fulfilled,
        lower(COALESCE(fulfillment_status, '')) IN ('partial', 'partially_fulfilled') AS is_partial_fulfillment,
        CASE
            WHEN first_shipped_at IS NULL THEN false
            ELSE CAST(first_shipped_at AS DATE) = CAST(order_timestamp AS DATE)
        END AS ship_same_day_flag,
        CASE
            WHEN status = 'OPEN' THEN date_diff('hour', order_timestamp, current_timestamp) > 24
            ELSE false
        END AS pending_gt_24h_flag,
        CASE
            WHEN status = 'OPEN' THEN date_diff('hour', order_timestamp, current_timestamp) > 48
            ELSE false
        END AS pending_gt_48h_flag
    FROM base
)
SELECT
    *,
    CASE
        WHEN hours_to_first_ship IS NULL THEN 'Not shipped'
        WHEN hours_to_first_ship < 4 THEN '<4h'
        WHEN hours_to_first_ship < 12 THEN '4-12h'
        WHEN hours_to_first_ship < 24 THEN '12-24h'
        ELSE '24h+'
    END AS first_ship_bucket,
    CASE
        WHEN hours_to_complete IS NULL THEN 'Not completed'
        WHEN hours_to_complete < 4 THEN '<4h'
        WHEN hours_to_complete < 12 THEN '4-12h'
        WHEN hours_to_complete < 24 THEN '12-24h'
        WHEN hours_to_complete < 72 THEN '1-3d'
        ELSE '3d+'
    END AS complete_time_bucket,
    CASE
        WHEN net_revenue < 200000 THEN 'Small'
        WHEN net_revenue < 1000000 THEN 'Medium'
        ELSE 'Large'
    END AS order_size_band
FROM flags

