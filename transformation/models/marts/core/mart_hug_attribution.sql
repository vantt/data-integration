{{ config(
    tags=['mart', 'crm', 'core'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- HUG campaign attribution: issued vs redeemed vouchers, revenue and margin per redemption.
-- Grain: one row per voucher code (unique per customer per campaign).

SELECT
    v.campaign_id,
    v.code,
    v.customer_id,
    c.customer_key,
    c.full_name,
    c.value_group,
    v.token,
    v.min_order_vnd,
    v.issued_at,
    v.redeemed_at,
    v.order_code,
    v.is_redeemed,
    -- Order-level financials (NULL when not redeemed).
    -- total_collected = amount paid by customer (after discount, incl. VAT).
    -- channel_net_profit from fact_order_economics = contribution margin (no overhead).
    o.total_collected                AS redemption_revenue_vnd,
    oe.channel_net_profit            AS redemption_margin_vnd,
    DATE_TRUNC('day', v.issued_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE   AS issued_date,
    DATE_TRUNC('day', v.redeemed_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE AS redeemed_date

FROM {{ ref('stg_crm__hug_voucher') }} v
LEFT JOIN {{ ref('dim_customers') }} c ON c.customer_id = v.customer_id
LEFT JOIN {{ ref('fact_orders') }} o
       ON o.order_code = v.order_code
LEFT JOIN {{ ref('fact_order_economics') }} oe
       ON oe.order_code = v.order_code
