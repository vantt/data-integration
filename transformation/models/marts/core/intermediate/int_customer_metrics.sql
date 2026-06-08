{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'intermediate']
) }}

WITH orders AS (
    SELECT * FROM {{ ref('fact_orders') }}
),

sales AS (
    SELECT * FROM {{ ref('fact_sales') }}
),

channels AS (
    SELECT * FROM {{ ref('dim_channels') }}
),

products AS (
    SELECT * FROM {{ ref('dim_products') }}
),

payments AS (
    SELECT * FROM {{ ref('fact_payments') }}
),

payment_methods AS (
    SELECT * FROM {{ ref('dim_payment_methods') }}
),

-- Determine which customers need processing
changed_customers AS (
    {% if is_incremental() %}
    SELECT DISTINCT customer_key
    FROM orders
    WHERE updated_at >= (SELECT MAX(last_order_date) FROM {{ this }})
    {% else %}
    SELECT DISTINCT customer_key FROM orders
    {% endif %}
),

customer_orders AS (
    SELECT
        o.customer_key,
        o.order_id,
        o.ordered_at,
        o.total_collected
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
),

-- RFM aggregations (existing)
aggregated AS (
    SELECT
        customer_key,
        MIN(ordered_at) as first_order_date,
        MAX(ordered_at) as last_order_date,
        COUNT(DISTINCT order_id) as frequency,
        SUM(total_collected) as monetary_value
    FROM customer_orders
    GROUP BY customer_key
),

-- Channel preference: mode of channel_format per customer (count ORDERS, not line items)
channel_stats AS (
    SELECT
        s.customer_key,
        c.channel_format,
        COUNT(DISTINCT s.order_id) as order_count
    FROM sales s
    JOIN channels c ON s.channel_key = c.channel_key
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON s.customer_key = cc.customer_key
    {% endif %}
    WHERE c.is_sales_channel = true
    GROUP BY s.customer_key, c.channel_format
),

channel_ranked AS (
    SELECT
        customer_key,
        channel_format,
        ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY order_count DESC, channel_format ASC) as rn
    FROM channel_stats
),

channel_preference_cte AS (
    SELECT
        customer_key,
        CASE channel_format
            WHEN 'Social' THEN 'CHANNEL_SOCIAL'
            WHEN 'Marketplace' THEN 'CHANNEL_MARKETPLACE'
            WHEN 'Web' THEN 'CHANNEL_DIRECT'
            WHEN 'Direct' THEN 'CHANNEL_DIRECT'
            WHEN 'B2B' THEN 'CHANNEL_DIRECT'
            WHEN 'Retail' THEN 'CHANNEL_OFFLINE'
            ELSE 'CHANNEL_OTHER'
        END as channel_preference
    FROM channel_ranked
    WHERE rn = 1
),

-- Acquisition source: channel_name of the customer's FIRST order (earliest ordered_at).
-- Sapo customer payload has no acquisition/source/UTM field, so we proxy "where acquired"
-- by the specific channel through which the customer first transacted. Stored as the raw
-- channel_name (kept specific — roll up to format/category via dim_channels at query time).
-- Validated by a relationships test (-> dim_channels.channel_name), not a fixed enum.
-- Ties broken by order_id.
first_order_channel AS (
    SELECT customer_key, channel_name AS acquisition_source
    FROM (
        SELECT
            o.customer_key,
            ch.channel_name,
            ROW_NUMBER() OVER (
                PARTITION BY o.customer_key
                ORDER BY o.ordered_at ASC, o.order_id ASC
            ) AS rn
        FROM orders o
        JOIN channels ch ON o.channel_key = ch.channel_key
        {% if is_incremental() %}
        INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
        {% endif %}
        WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
    ) ranked
    WHERE rn = 1
),

-- Product affinity: brand with >60% revenue share
brand_revenue AS (
    SELECT
        s.customer_key,
        p.brand_name,
        SUM(s.net_revenue) as brand_revenue
    FROM sales s
    JOIN products p ON s.product_key = p.product_key
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON s.customer_key = cc.customer_key
    {% endif %}
    WHERE p.brand_name IS NOT NULL AND p.brand_name != 'Unknown'
    GROUP BY s.customer_key, p.brand_name
),

customer_total_revenue AS (
    SELECT
        customer_key,
        SUM(brand_revenue) as total_revenue
    FROM brand_revenue
    GROUP BY customer_key
),

brand_share AS (
    SELECT
        br.customer_key,
        br.brand_name,
        br.brand_revenue / NULLIF(ctr.total_revenue, 0) as share
    FROM brand_revenue br
    JOIN customer_total_revenue ctr ON br.customer_key = ctr.customer_key
),

product_affinity_cte AS (
    SELECT
        customer_key,
        CASE
            WHEN MAX(share) FILTER (WHERE brand_name = 'Fine Japan Vietnam') > 0.6 THEN 'PRODUCT_FINE_JAPAN'
            WHEN MAX(share) FILTER (WHERE brand_name = 'FG Care') > 0.6 THEN 'PRODUCT_FG_CARE'
            WHEN MAX(share) FILTER (WHERE brand_name = 'Fine Care') > 0.6 THEN 'PRODUCT_FINE_CARE'
            ELSE 'PRODUCT_MULTI'
        END as product_affinity
    FROM brand_share
    GROUP BY customer_key
),

-- Payment behavior: COD vs prepaid (simplified - no debt tracking available)
order_payments AS (
    SELECT
        o.customer_key,
        o.order_id,
        pm.payment_method_type
    FROM orders o
    JOIN payments p ON o.order_id = p.order_id
    JOIN payment_methods pm ON p.payment_method_key = pm.payment_method_key
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
),

payment_stats AS (
    SELECT
        customer_key,
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT order_id) FILTER (WHERE payment_method_type = 'cod') as cod_orders
    FROM order_payments
    GROUP BY customer_key
),

payment_behavior_cte AS (
    SELECT
        customer_key,
        CASE
            WHEN cod_orders::float / NULLIF(total_orders, 0) > 0.7 THEN 'PAYMENT_COD'
            ELSE 'PAYMENT_PREPAID'
        END as payment_behavior
    FROM payment_stats
),

-- Average order spend (total_collected-based) for customer scoring — not dashboard AOV
avg_order_spend_cte AS (
    SELECT
        o.customer_key,
        ROUND(SUM(o.total_collected) / NULLIF(COUNT(DISTINCT o.order_id), 0))::BIGINT AS avg_order_spend
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
    GROUP BY o.customer_key
),

-- Inter-purchase interval: average days between consecutive non-cancelled, non-draft orders.
-- Excludes 0-day gaps (same-session/same-day orders) to measure inter-visit cycle, not intra-day repeats.
order_sequence AS (
    SELECT
        o.customer_key,
        o.ordered_at,
        LAG(o.ordered_at) OVER (
            PARTITION BY o.customer_key ORDER BY o.ordered_at
        ) AS prev_ordered_at
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
),

inter_purchase_cte AS (
    SELECT
        customer_key,
        ROUND(AVG(
            date_diff('day', CAST(prev_ordered_at AS DATE), CAST(ordered_at AS DATE))
        ))::INTEGER AS avg_days_between_orders
    FROM order_sequence
    WHERE prev_ordered_at IS NOT NULL
      AND date_diff('day', CAST(prev_ordered_at AS DATE), CAST(ordered_at AS DATE)) > 0
    GROUP BY customer_key
),

-- Discount sensitivity: share of non-cancelled/draft orders that had any discount applied.
-- NULL when customer has no qualifying orders (distinct from 0 = never discounted).
discount_rate_cte AS (
    SELECT
        o.customer_key,
        CAST(COUNT(DISTINCT o.order_id) FILTER (WHERE o.discount_amount > 0) AS DOUBLE)
            / NULLIF(COUNT(DISTINCT o.order_id), 0) AS discount_order_rate
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
    GROUP BY o.customer_key
),

-- Cancel rate: share of attempted orders (excl. drafts) that were cancelled.
cancel_rate_cte AS (
    SELECT
        o.customer_key,
        CAST(COUNT(DISTINCT o.order_id) FILTER (WHERE o.status = 'CANCELLED') AS DOUBLE)
            / NULLIF(COUNT(DISTINCT o.order_id), 0) AS cancel_rate
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
    WHERE o.status != 'DRAFT'
    GROUP BY o.customer_key
)

SELECT
    a.customer_key,
    a.first_order_date,
    a.last_order_date,
    date_diff('day', CAST(a.last_order_date AS DATE), current_date) as recency_days,
    a.frequency,
    a.monetary_value,
    date_diff('day', CAST(a.first_order_date AS DATE), CAST(a.last_order_date AS DATE)) as lifespan_days,

    -- P2 dimensions
    COALESCE(cp.channel_preference, 'CHANNEL_OTHER') as channel_preference,
    COALESCE(pa.product_affinity, 'PRODUCT_MULTI') as product_affinity,
    COALESCE(pb.payment_behavior, 'PAYMENT_PREPAID') as payment_behavior,
    foc.acquisition_source,                       -- channel_name of first order (NULL if no orders)

    -- P3 metrics
    ip.avg_days_between_orders,
    abv.avg_order_spend,
    dr.discount_order_rate,                       -- NULL = no qualifying orders (not 0 = never discounted)
    COALESCE(cr.cancel_rate, 0.0) AS cancel_rate, -- 0 is correct when no cancellations on record
    CASE
        WHEN ip.avg_days_between_orders IS NOT NULL AND a.frequency > 1
        THEN CAST(a.last_order_date AS DATE) + (ip.avg_days_between_orders::VARCHAR || ' days')::INTERVAL
        ELSE NULL
    END AS predicted_next_purchase_date,

    current_timestamp as metric_calculated_at
FROM aggregated a
LEFT JOIN channel_preference_cte cp ON a.customer_key = cp.customer_key
LEFT JOIN first_order_channel foc ON a.customer_key = foc.customer_key
LEFT JOIN product_affinity_cte pa ON a.customer_key = pa.customer_key
LEFT JOIN payment_behavior_cte pb ON a.customer_key = pb.customer_key
LEFT JOIN avg_order_spend_cte abv ON a.customer_key = abv.customer_key
LEFT JOIN inter_purchase_cte ip ON a.customer_key = ip.customer_key
LEFT JOIN discount_rate_cte dr ON a.customer_key = dr.customer_key
LEFT JOIN cancel_rate_cte cr ON a.customer_key = cr.customer_key
