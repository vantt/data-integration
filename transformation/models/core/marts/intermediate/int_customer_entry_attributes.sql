{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'intermediate']
) }}

-- =============================================================================
-- INT: CUSTOMER ENTRY ATTRIBUTES
-- =============================================================================
-- One row per retail customer — entry-point attributes derived from their FIRST
-- order only. Entry attributes are immutable; once a customer has a first order
-- these values never change.
--
-- Downstream: mart_cohort_retention (cohort axis assignment)
--
-- Incremental: only processes customers not already in this table, since
-- entry attributes are defined at acquisition and never change.
-- =============================================================================

WITH retail_customers AS (
    -- Retail scope only
    SELECT customer_key
    FROM {{ ref('dim_customers') }}
    WHERE customer_type = 'RETAIL'
),

-- Step 1: Find the single first order per retail customer from a sales channel.
-- Excludes is_sales_channel=FALSE channels (Internal: US/Quà Tặng/Other/Unknown/etc.)
-- so internal-arrangement customers don't pollute cohort entry attributes.
first_orders AS (
    SELECT
        o.customer_key,
        o.order_id,
        o.ordered_at,
        o.channel_key,
        o.total_collected
    FROM {{ ref('fact_orders') }} o
    INNER JOIN retail_customers rc ON o.customer_key = rc.customer_key
    INNER JOIN {{ ref('dim_channels') }} ch ON o.channel_key = ch.channel_key
                                           AND ch.is_sales_channel = TRUE
    WHERE o.is_active_order = TRUE
      AND o.status NOT IN ('CANCELLED', 'DRAFT')
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY o.customer_key
        ORDER BY o.ordered_at ASC, o.order_id ASC
    ) = 1
),

-- Step 2: Basket size (COUNT DISTINCT product_key on first order lines)
-- Status filter inherited via INNER JOIN to first_orders (already gated on valid orders)
basket_counts AS (
    SELECT
        fs.customer_key,
        COUNT(DISTINCT fs.product_key) AS basket_size_num
    FROM {{ ref('fact_sales') }} fs
    INNER JOIN first_orders fo ON fs.customer_key = fo.customer_key
                               AND fs.order_id    = fo.order_id
    GROUP BY fs.customer_key
),

-- Step 3: Entry product (highest net_revenue line on first order, ties: min product_key)
-- Status filter inherited via INNER JOIN to first_orders
entry_product AS (
    SELECT
        fs.customer_key,
        fs.product_key
    FROM {{ ref('fact_sales') }} fs
    INNER JOIN first_orders fo ON fs.customer_key = fo.customer_key
                               AND fs.order_id    = fo.order_id
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY fs.customer_key
        ORDER BY fs.net_revenue DESC, fs.product_key ASC
    ) = 1
),

-- Step 4: Join everything to produce final entry attributes
customers_entry AS (
    SELECT
        fo.customer_key,
        DATE_TRUNC('month', fo.ordered_at)::DATE              AS first_order_month,
        fo.ordered_at                                         AS first_order_at,
        fo.channel_key                                        AS acquisition_channel_key,
        ch.channel_name                                       AS acquisition_channel_name,
        ep.product_key                                        AS entry_product_key,
        p.product_name                                        AS entry_product_name,
        COALESCE(p.category, 'Khác')                         AS entry_category,
        COALESCE(bc.basket_size_num, 1)::INTEGER              AS basket_size_num,
        fo.total_collected                                    AS first_order_total
    FROM first_orders fo
    LEFT JOIN basket_counts bc    ON fo.customer_key = bc.customer_key
    LEFT JOIN entry_product ep    ON fo.customer_key = ep.customer_key
    LEFT JOIN {{ ref('dim_channels') }} ch  ON fo.channel_key  = ch.channel_key
    LEFT JOIN {{ ref('dim_products') }} p   ON ep.product_key  = p.product_key
)

SELECT
    customer_key,
    first_order_month,
    first_order_at,
    acquisition_channel_key,
    acquisition_channel_name,
    entry_product_key,
    entry_product_name,
    entry_category,
    basket_size_num,
    CASE
        WHEN basket_size_num >= 2 THEN '≥2'
        ELSE '1'
    END                                                       AS basket_size,
    first_order_total::BIGINT                                 AS first_order_total,
    CASE
        WHEN first_order_total < 300000       THEN 'LOW'
        WHEN first_order_total < 1000000      THEN 'MID'
        WHEN first_order_total < 3000000      THEN 'HIGH'
        ELSE                                       'PREMIUM'
    END                                                       AS entry_value_band

FROM customers_entry

{% if is_incremental() %}
-- Entry attributes are immutable: only process customers not yet present.
-- IMMUTABILITY ASSUMPTION: first-order status is treated as fixed at capture time.
-- If a customer's first order is later cancelled and re-included by a status change,
-- their entry attributes will NOT update — run dbt --full-refresh to correct.
-- NOT IN performance degrades as the table grows; acceptable while customer count
-- remains in the hundreds of thousands. Switch to NOT EXISTS if scan time becomes
-- noticeable (each run full-scans {{ this }}).
WHERE customer_key NOT IN (SELECT customer_key FROM {{ this }})
{% endif %}
