{{ config(
    tags=['int', 'shopee'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Shopee per-order fee breakdown: revenue LEFT JOIN service_fees.
-- Intermediate enrichment layer — NOT a primary fact (all orders exist in Sapo fact_orders).
-- Rolling location for P0 Metabase access; P1 joins into fact_order_economics.

WITH rev AS (
    SELECT * FROM {{ ref('stg_shopee_order_revenue') }}
),

fees AS (
    SELECT * FROM {{ ref('stg_shopee_order_service_fees') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['rev.order_code']) }} AS shopee_order_sk,
    rev.order_code,
    rev.order_placed_at,
    rev.payout_released_at,
    rev.order_type,
    rev.payment_method,
    rev.buyer_username,

    -- Revenue
    rev.total_paid_amount,
    rev.product_list_price,
    rev.refund_amount,
    rev.gross_revenue,

    -- Shipping
    rev.total_shipping_net,
    rev.shipping_fee_paid_by_buyer,
    rev.shipping_fee_actual,
    rev.shipping_subsidy_from_shopee,

    -- Discounts / subsidies
    rev.total_discounts,

    -- Platform fees (from Doanh thu)
    rev.total_platform_fees,
    rev.service_fee,
    rev.payment_fee,
    rev.fixed_fee,

    -- Extra service fees (from Service Fee Details sheet)
    COALESCE(fees.infrastructure_fee, 0) AS infrastructure_fee,
    COALESCE(fees.voucher_xtra_fee, 0)   AS voucher_xtra_fee,

    -- Taxes
    rev.total_taxes,
    rev.vat_tax,
    rev.personal_income_tax,

    -- Derived net settlement (matches Shopee "Tổng phát hành")
    (
        rev.total_paid_amount
        + rev.total_shipping_net
        + rev.total_discounts
        + rev.total_platform_fees
        + rev.total_taxes
        + COALESCE(fees.infrastructure_fee, 0)
        + COALESCE(fees.voucher_xtra_fee, 0)
    ) AS net_settlement,

    -- Lineage
    rev.source_file,
    rev.ingested_at

FROM rev
LEFT JOIN fees USING (order_code)
