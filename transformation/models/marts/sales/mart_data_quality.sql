{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Single-row system data-quality / coverage snapshot for the detailView "Data health"
-- surface. Recomputed every pipeline run; the app reads it as one cheap SELECT (1 row).
-- Grain: 1 row (dq_key='global'). Cross-join of single-row CTEs.

WITH econ AS (
    SELECT
        count(*)                              AS total_orders,
        count(*) FILTER (WHERE has_cogs)          AS cogs_matched,
        count(*) FILTER (WHERE has_platform_fees) AS fees_matched
    FROM {{ ref('fact_order_economics') }}
),
ordcnt AS ( SELECT count(*) AS n FROM {{ ref('fact_orders') }} ),
uscnt  AS ( SELECT count(*) AS n FROM {{ ref('fact_us_shipment_economics') }} ),
ship AS (
    SELECT
        count(*)                                  AS total,
        count(*) FILTER (WHERE carrier_id IS NULL) AS carrier_null,
        count(DISTINCT order_code)                 AS orders_with_ship
    FROM {{ ref('fact_fulfillments') }}
),
ret AS (
    SELECT count(DISTINCT r.order_code) AS n
    FROM {{ ref('fact_order_returns') }} r
    JOIN {{ ref('fact_orders') }} o ON r.order_code = o.order_code
),
cust AS (
    SELECT
        count(*)                                       AS total,
        count(*) FILTER (WHERE acquisition_source IS NULL) AS acq_null
    FROM {{ ref('dim_customers') }}
)

SELECT
    'global'                                                          AS dq_key,
    now()                                                            AS as_of_ict,  -- TIMESTAMPTZ; serving + app sessions use Asia/Ho_Chi_Minh, so it displays ICT
    econ.total_orders,
    round(100.0 * econ.cogs_matched     / nullif(econ.total_orders, 0), 1) AS cogs_rate_pct,
    round(100.0 * econ.fees_matched     / nullif(econ.total_orders, 0), 1) AS platform_fees_rate_pct,
    round(100.0 * ship.orders_with_ship / nullif(ordcnt.n, 0), 1)          AS fulfillment_coverage_pct,
    round(100.0 * ret.n                 / nullif(ordcnt.n, 0), 1)          AS return_rate_pct,
    round(100.0 * uscnt.n               / nullif(ordcnt.n, 0), 1)          AS us_share_pct,
    round(100.0 * ship.carrier_null     / nullif(ship.total, 0), 1)        AS carrier_null_rate_pct,
    round(100.0 * cust.acq_null         / nullif(cust.total, 0), 1)        AS acq_source_null_rate_pct
FROM econ, ordcnt, uscnt, ship, ret, cust
