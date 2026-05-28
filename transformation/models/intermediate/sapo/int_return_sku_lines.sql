{{ config(
    tags=['int', 'sapo', 'returns'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INTERMEDIATE: RETURN × SKU LINES (CASE B approximation)
-- =================================================================================================
-- Context: Sapo's return API is order-level only — no line-item breakdown per return event.
-- Approach: Join fact_order_returns → fact_orders → fact_sales (order items grain) to surface
--   the SKUs that were part of a returned order.
--
-- CAVEAT (document in all downstream queries):
--   When one order has multiple SKUs and only one SKU was actually returned, all SKUs in that
--   order appear here. This is an APPROXIMATION — "SKUs present in returned orders", not
--   "SKUs confirmed returned". Use for triage / ranking direction, not precise per-SKU refund.
--
-- Refund allocation: refund_amount is distributed proportionally by line revenue share within
--   the order (best approximation given data constraints).
--
-- Grain: one row per (return_id, product_key) — multiple SKUs per return possible.
-- =================================================================================================

WITH returns AS (
    SELECT
        return_id,
        order_code,
        return_date,
        refund_amount,
        return_quantity,
        return_reason,
        return_status,
        refund_status,
        channel_key,
        date_key
    FROM {{ ref('fact_order_returns') }}
    WHERE return_status IS DISTINCT FROM 'CANCELLED'
),

-- order_id bridge (fact_orders holds both order_code and order_id)
order_bridge AS (
    SELECT order_code, order_id
    FROM {{ ref('fact_orders') }}
),

-- SKU lines from Sapo order items (via fact_sales)
order_sku_lines AS (
    SELECT
        fs.order_id,
        fs.product_key,
        fs.quantity                         AS sold_quantity,
        fs.revenue                          AS line_revenue
    FROM {{ ref('fact_sales') }} fs
    WHERE fs.revenue > 0
),

-- Order-level revenue totals for proportional allocation
order_revenue_totals AS (
    SELECT
        order_id,
        SUM(revenue) AS total_order_revenue
    FROM {{ ref('fact_sales') }}
    WHERE revenue > 0
    GROUP BY order_id
),

-- Join: returns → order_bridge → sku_lines
joined AS (
    SELECT
        r.return_id,
        r.order_code,
        ob.order_id,
        r.return_date,
        r.refund_amount,
        r.return_quantity,
        r.return_reason,
        r.return_status,
        r.refund_status,
        r.channel_key,
        r.date_key,
        osl.product_key,
        osl.sold_quantity,
        osl.line_revenue,
        ort.total_order_revenue
    FROM returns r
    JOIN order_bridge ob ON r.order_code = ob.order_code
    JOIN order_sku_lines osl ON ob.order_id = osl.order_id
    LEFT JOIN order_revenue_totals ort ON ob.order_id = ort.order_id
)

SELECT
    -- Surrogate / natural keys
    {{ dbt_utils.generate_surrogate_key(['return_id', 'product_key']) }} AS return_sku_key,
    return_id,
    order_code,
    product_key,

    -- Temporal
    return_date,
    date_key,

    -- Dimensions
    return_reason,
    return_status,
    refund_status,
    channel_key,

    -- Metrics
    sold_quantity,

    -- Proportional refund allocation: line_revenue / order_revenue × total_refund
    ROUND(
        COALESCE(line_revenue, 0)
        / NULLIF(total_order_revenue, 0)
        * COALESCE(refund_amount, 0),
        2
    )                                                           AS refund_amount_allocated,

    -- Raw order-level refund (for aggregation sanity checks)
    refund_amount                                               AS refund_amount_order_total

FROM joined
