-- Guard: phase-07 removed the Shopee service_fee D-aggregate (it double-counted
-- the F-detail infrastructure_fee + voucher_xtra_fee). No platform_service cost rows must remain.

SELECT order_id, order_code, amount
FROM {{ ref('fact_order_costs') }}
WHERE cost_type = 'platform_service'
