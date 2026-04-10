{{ config(materialized='view', tags=['stg', 'shopee']) }}

-- Shopee order-level revenue: type casting, numeric cleanup, convenience fields.

SELECT
    order_code,
    CAST(order_placed_at AS DATE)          AS order_placed_at,
    CAST(payout_released_at AS DATE)       AS payout_released_at,
    order_type,
    payment_method,
    buyer_username,
    seller_tax_code,

    -- Revenue
    CAST(total_paid_amount AS BIGINT)      AS total_paid_amount,
    CAST(product_list_price AS BIGINT)     AS product_list_price,
    CAST(refund_amount AS BIGINT)          AS refund_amount,

    -- Shipping (6 components)
    CAST(shipping_fee_paid_by_buyer AS BIGINT)   AS shipping_fee_paid_by_buyer,
    CAST(shipping_fee_actual AS BIGINT)          AS shipping_fee_actual,
    CAST(shipping_subsidy_from_shopee AS BIGINT) AS shipping_subsidy_from_shopee,
    CAST(shipping_fee_return_refund AS BIGINT)   AS shipping_fee_return_refund,
    CAST(shipping_refund_by_piship AS BIGINT)    AS shipping_refund_by_piship,
    CAST(shipping_fee_failed_delivery AS BIGINT) AS shipping_fee_failed_delivery,

    -- Discounts & subsidies
    CAST(product_subsidy_from_shopee AS BIGINT)        AS product_subsidy_from_shopee,
    CAST(seller_voucher_discount AS BIGINT)            AS seller_voucher_discount,
    CAST(seller_cofunded_voucher_discount AS BIGINT)   AS seller_cofunded_voucher_discount,
    CAST(seller_coin_cashback AS BIGINT)               AS seller_coin_cashback,
    CAST(seller_cofunded_coin_cashback AS BIGINT)      AS seller_cofunded_coin_cashback,

    -- Platform fees
    CAST(fixed_fee AS BIGINT)              AS fixed_fee,
    CAST(service_fee AS BIGINT)            AS service_fee,
    CAST(payment_fee AS BIGINT)            AS payment_fee,
    CAST(affiliate_commission_fee AS BIGINT) AS affiliate_commission_fee,
    CAST(piship_service_fee AS BIGINT)     AS piship_service_fee,
    CAST(auto_topup_amount AS BIGINT)      AS auto_topup_amount,

    -- Taxes
    CAST(vat_tax AS BIGINT)                AS vat_tax,
    CAST(personal_income_tax AS BIGINT)    AS personal_income_tax,

    -- Derived convenience fields
    COALESCE(CAST(total_paid_amount AS BIGINT), 0)
        + COALESCE(CAST(refund_amount AS BIGINT), 0)
        AS gross_revenue,

    COALESCE(CAST(shipping_fee_paid_by_buyer AS BIGINT), 0)
        + COALESCE(CAST(shipping_fee_actual AS BIGINT), 0)
        + COALESCE(CAST(shipping_subsidy_from_shopee AS BIGINT), 0)
        + COALESCE(CAST(shipping_fee_return_refund AS BIGINT), 0)
        + COALESCE(CAST(shipping_refund_by_piship AS BIGINT), 0)
        + COALESCE(CAST(shipping_fee_failed_delivery AS BIGINT), 0)
        AS total_shipping_net,

    COALESCE(CAST(seller_voucher_discount AS BIGINT), 0)
        + COALESCE(CAST(seller_cofunded_voucher_discount AS BIGINT), 0)
        + COALESCE(CAST(seller_coin_cashback AS BIGINT), 0)
        + COALESCE(CAST(seller_cofunded_coin_cashback AS BIGINT), 0)
        + COALESCE(CAST(product_subsidy_from_shopee AS BIGINT), 0)
        AS total_discounts,

    COALESCE(CAST(fixed_fee AS BIGINT), 0)
        + COALESCE(CAST(service_fee AS BIGINT), 0)
        + COALESCE(CAST(payment_fee AS BIGINT), 0)
        + COALESCE(CAST(affiliate_commission_fee AS BIGINT), 0)
        + COALESCE(CAST(piship_service_fee AS BIGINT), 0)
        + COALESCE(CAST(auto_topup_amount AS BIGINT), 0)
        AS total_platform_fees,

    COALESCE(CAST(vat_tax AS BIGINT), 0)
        + COALESCE(CAST(personal_income_tax AS BIGINT), 0)
        AS total_taxes,

    -- Lineage
    source_file,
    ingested_at

FROM {{ ref('src_shopee_order_revenue') }}
