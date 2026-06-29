{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'intermediate']
) }}

-- Per-customer discount metrics across 4 unified buckets.
-- Grain: 1 row per customer_key.
-- Buckets:
--   line_discount  = item-level price reduction (fact_sales.discount_rate)
--   voucher        = customer actively redeemed a voucher code
--   campaign       = merchant applied promo: bundle/CTKM/sampling
--   negotiated     = B2B/direct deal: đại lý/hợp đồng/nhân viên/overseas

WITH changed_customers AS (
    {% if is_incremental() %}
    SELECT DISTINCT customer_key
    FROM {{ ref('fact_orders') }}
    WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '1 day' FROM {{ this }})
    {% else %}
    SELECT DISTINCT customer_key FROM {{ ref('fact_orders') }}
    {% endif %}
),

-- ── BUCKET 1: line_discount ───────────────────────────────────────────────
-- Source: fact_sales.discount_rate (item-level, no type label available)
-- Aggregate to order-level (max rate across discounted lines), then to customer.
line_discount_per_order AS (
    SELECT
        fs.customer_key,
        fs.order_id,
        fo.ordered_at,
        MAX(fs.discount_rate) AS order_line_max_rate
    FROM {{ ref('fact_sales') }} fs
    JOIN {{ ref('fact_orders') }} fo ON fs.order_id = fo.order_id
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON fs.customer_key = cc.customer_key
    {% endif %}
    WHERE fs.discount_amount > 0
      AND fs.discount_rate IS NOT NULL
      AND fo.is_active_order
    GROUP BY fs.customer_key, fs.order_id, fo.ordered_at
),

line_discount_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key
            ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM line_discount_per_order
),

line_discount_cte AS (
    SELECT
        customer_key,
        MAX(order_line_max_rate) FILTER (WHERE rn_desc = 1) AS last_line_discount_rate,
        MAX(order_line_max_rate)                             AS max_line_discount_rate
    FROM line_discount_ranked
    GROUP BY customer_key
),

-- ── Shared helper: order-level discount facts ─────────────────────────────
-- Used by buckets 2-4. Filter by primary_discount_type per bucket.
order_discount_facts AS (
    SELECT
        fo.customer_key,
        fo.order_id,
        fo.ordered_at,
        fo.max_discount_rate,
        fo.primary_discount_type
    FROM {{ ref('fact_orders') }} fo
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON fo.customer_key = cc.customer_key
    {% endif %}
    WHERE fo.is_active_order
      AND fo.max_discount_rate IS NOT NULL
      AND fo.primary_discount_type IS NOT NULL
),

-- ── BUCKET 2: voucher ─────────────────────────────────────────────────────
-- Customer actively redeemed a seller voucher code.
voucher_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type = 'voucher_promotional'
),

voucher_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_voucher_discount_rate,
        MAX(max_discount_rate)                             AS max_voucher_discount_rate
    FROM voucher_ranked
    GROUP BY customer_key
),

-- ── BUCKET 3: campaign ────────────────────────────────────────────────────
-- Merchant proactively applied: bundle deal, CTKM, sampling/gift.
campaign_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type IN ('bundle', 'campaign', 'sampling_gift')
),

campaign_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_campaign_discount_rate,
        MAX(max_discount_rate)                             AS max_campaign_discount_rate
    FROM campaign_ranked
    GROUP BY customer_key
),

-- ── BUCKET 4: negotiated ──────────────────────────────────────────────────
-- Direct deal: đại lý, hợp đồng, nhân viên/CTV, khách US.
negotiated_ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key ORDER BY ordered_at DESC, order_id DESC
        ) AS rn_desc
    FROM order_discount_facts
    WHERE primary_discount_type IN (
        'negotiated_micro', 'negotiated_standard', 'negotiated_deep',
        'wholesale_explicit', 'employee_internal', 'overseas'
    )
),

negotiated_cte AS (
    SELECT
        customer_key,
        MAX(max_discount_rate) FILTER (WHERE rn_desc = 1) AS last_negotiated_discount_rate,
        MAX(max_discount_rate)                             AS max_negotiated_discount_rate
    FROM negotiated_ranked
    GROUP BY customer_key
),

all_customers AS (
    SELECT DISTINCT fo.customer_key
    FROM {{ ref('fact_orders') }} fo
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON fo.customer_key = cc.customer_key
    {% endif %}
    WHERE fo.is_active_order
)

SELECT
    ac.customer_key,
    ld.last_line_discount_rate,
    ld.max_line_discount_rate,
    v.last_voucher_discount_rate,
    v.max_voucher_discount_rate,
    c.last_campaign_discount_rate,
    c.max_campaign_discount_rate,
    n.last_negotiated_discount_rate,
    n.max_negotiated_discount_rate,
    current_timestamp AS metric_calculated_at
FROM all_customers ac
LEFT JOIN line_discount_cte ld ON ac.customer_key = ld.customer_key
LEFT JOIN voucher_cte        v  ON ac.customer_key = v.customer_key
LEFT JOIN campaign_cte       c  ON ac.customer_key = c.customer_key
LEFT JOIN negotiated_cte     n  ON ac.customer_key = n.customer_key
