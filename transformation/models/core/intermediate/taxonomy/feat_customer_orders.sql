{{ config(materialized='table', tags=['taxonomy']) }}
-- Order features of the classification engine: the channel names a customer has a non-cancelled
-- order on. Same join and filter as the us_channel_customers CTE of dim_customers
-- (fact_orders JOIN dim_channels, status != 'CANCELLED', so a NULL status is excluded too), keyed by
-- channel NAME as there ('US'). A customer without such an order has no row; the engine reads the
-- missing list as [] (never NULL), like the EXISTS it replaces.
SELECT
    fo.customer_key,
    COALESCE(
        list(DISTINCT ch.channel_name ORDER BY ch.channel_name) FILTER (WHERE ch.channel_name IS NOT NULL),
        CAST([] AS VARCHAR[])
    ) AS channels_ordered_on
FROM {{ ref('fact_orders') }} fo
JOIN {{ ref('dim_channels') }} ch ON fo.channel_key = ch.channel_key
WHERE fo.status != 'CANCELLED'
GROUP BY fo.customer_key
