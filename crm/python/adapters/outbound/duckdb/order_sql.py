"""SQL constants for CRM order detail DuckDB queries.

All queries mirror the Go adapter (order_repo_fetch.go) exactly — same table
names, same column aliases, same CAST AS DOUBLE pattern for DECIMAL columns.

Parameterised with positional ? placeholders (DuckDB native binding).
"""

HEADER_SQL = """
SELECT
    fo.order_id, fo.order_code, fo.customer_key,
    fo.status, fo.payment_status, fo.fulfillment_status,
    fo.ordered_at                                         AS created_at,
    fo.first_shipped_at, fo.updated_at,
    CAST(fo.time_to_complete_hours  AS DOUBLE)            AS time_to_complete_hours,
    fo.shipping_address,
    CAST(fo.max_discount_rate       AS DOUBLE)            AS max_discount_rate,
    fo.primary_discount_type,
    CAST(fo.gross_revenue    AS DOUBLE)                   AS gross_revenue,
    CAST(fo.discount_amount  AS DOUBLE)                   AS discount_amount,
    CAST(fo.net_revenue      AS DOUBLE)                   AS net_revenue,
    CAST(fo.vat_amount       AS DOUBLE)                   AS vat_amount,
    CAST(fo.total_collected  AS DOUBLE)                   AS total_collected,
    CAST(foe.cogs_amount              AS DOUBLE)          AS cogs_amount,
    CAST(foe.gross_profit             AS DOUBLE)          AS gross_profit,
    CAST(foe.gross_margin_pct         AS DOUBLE)          AS gross_margin_pct,
    CAST(foe.channel_net_profit       AS DOUBLE)          AS channel_net_profit,
    CAST(foe.channel_net_margin_pct   AS DOUBLE)          AS channel_net_margin_pct,
    CAST(foe.shopee_platform_fees     AS DOUBLE)          AS shopee_platform_fees,
    CAST(foe.shopee_infra_fee         AS DOUBLE)          AS shopee_infra_fee,
    CAST(foe.shopee_voucher_xtra_fee  AS DOUBLE)          AS shopee_voucher_xtra_fee,
    CAST(foe.shopee_taxes             AS DOUBLE)          AS shopee_taxes,
    CAST(foe.shopee_net_settlement    AS DOUBLE)          AS shopee_net_settlement,
    CAST(foe.cod_amount               AS DOUBLE)          AS cod_amount,
    foe.carrier_id,
    CAST(foe.return_amount            AS DOUBLE)          AS return_amount,
    foe.return_count,
    foe.has_cogs, foe.has_platform_fees, foe.has_returns,
    CAST(foe.promo_goods_cost         AS DOUBLE)          AS promo_goods_cost,
    CAST(foe.allocated_overhead       AS DOUBLE)          AS allocated_overhead,
    foe.is_overhead_estimated,
    CAST(foe.fully_loaded_net_profit  AS DOUBLE)          AS fully_loaded_net_profit,
    CAST(foe.fully_loaded_margin_pct  AS DOUBLE)          AS fully_loaded_margin_pct,
    foe.cogs_source,
    CAST(us.total_us_revenue_excl_vat AS DOUBLE)          AS total_us_revenue_excl_vat,
    CAST(us.total_us_revenue_incl_vat AS DOUBLE)          AS total_us_revenue_incl_vat,
    us.line_item_count                                    AS us_line_item_count,
    us.has_unpriced_sku, us.unpriced_sku_count,
    (us.order_id IS NOT NULL)                             AS is_us,
    ch.channel_name, ch.channel_code, ch.channel_category, ch.channel_format,
    ch.platform, ch.channel_brand, ch.market,
    pr.promotion_code,
    seller.full_name   AS seller_name, seller.email AS seller_email,
    creator.full_name  AS creator_name,
    tm.team_name, bl.branch_location_name AS branch_name,
    geo.province, geo.district, geo.ward, geo.country,
    cust.customer_id   AS cust_customer_id,
    cust.full_name     AS cust_full_name,
    cust.customer_type AS cust_customer_type,
    cust.value_group   AS cust_value_group,
    CAST(cust.lifetime_value AS DOUBLE) AS cust_lifetime_value
FROM fact_orders fo
LEFT JOIN fact_order_economics foe      ON fo.order_id = foe.order_id
LEFT JOIN fact_us_shipment_economics us ON fo.order_id = us.order_id
LEFT JOIN dim_channels ch               ON fo.channel_key = ch.channel_key
LEFT JOIN dim_promotions pr             ON fo.promotion_key = pr.promotion_key
LEFT JOIN dim_staff seller              ON fo.seller_staff_key = seller.staff_key
LEFT JOIN dim_staff creator             ON fo.creator_staff_key = creator.staff_key
LEFT JOIN dim_teams tm                  ON fo.team_key = tm.team_key
LEFT JOIN dim_branch_location bl        ON fo.branch_location_key = bl.branch_location_key
LEFT JOIN dim_geography geo             ON fo.shipping_geography_key = geo.geography_key
LEFT JOIN dim_customers cust            ON fo.customer_key = cust.customer_key
WHERE UPPER(fo.order_code) = UPPER(?)
LIMIT 1
"""

LINE_ITEMS_SQL = """
SELECT fs.order_line_id, dp.sku, dp.product_name, dp.variant_name,
       dp.brand_name, dp.category, dp.unit,
       CAST(fs.quantity                    AS DOUBLE) AS quantity,
       CAST(fs.net_revenue                 AS DOUBLE) AS revenue,
       CAST(fs.discount_amount             AS DOUBLE) AS discount_amount,
       CAST(fs.distributed_discount_amount AS DOUBLE) AS distributed_discount_amount,
       CAST(fs.weight_grams                AS DOUBLE) AS weight_grams
FROM fact_sales fs
LEFT JOIN dim_products dp ON fs.product_key = dp.product_key
WHERE fs.order_id = ?
ORDER BY fs.order_line_id
"""

COSTS_SQL = """
SELECT cost_type, cost_category,
       CAST(amount        AS DOUBLE) AS amount,
       CAST(discount_rate AS DOUBLE) AS discount_rate,
       discount_type, source_system, source_record, fee_source
FROM fact_order_costs
WHERE order_id = ?
ORDER BY cost_category, cost_type
"""

PAYMENTS_SQL = """
SELECT pm.payment_method_name, pm.payment_method_type,
       CAST(fp.amount AS DOUBLE) AS amount,
       fp.status, fp.payment_timestamp, fp.paid_on
FROM fact_payments fp
LEFT JOIN dim_payment_methods pm ON fp.payment_method_key = pm.payment_method_key
WHERE fp.order_id = ?
ORDER BY fp.payment_timestamp
"""

RETURNS_SQL = """
SELECT return_date,
       CAST(refund_amount AS DOUBLE) AS refund_amount,
       return_quantity, return_status, refund_status, return_reason
FROM fact_order_returns
WHERE UPPER(order_code) = UPPER(?)
ORDER BY return_date
"""

SHIPMENTS_SQL = """
SELECT fulfillment_id, fulfillment_code, tracking_code, carrier_id,
       shipping_service, status,
       CAST(cod_amount AS DOUBLE) AS cod_amount,
       created_at, shipped_at
FROM fact_fulfillments
WHERE UPPER(order_code) = UPPER(?)
ORDER BY shipped_at NULLS LAST, created_at
"""

COGS_ITEMS_SQL = """
SELECT r.sku, r.variant_id,
       CAST(r.cogs_goods_sapo    AS DOUBLE) AS cogs_goods_sapo,
       CAST(r.cogs_goods_misa    AS DOUBLE) AS cogs_goods_misa,
       CAST(r.cogs_goods_primary AS DOUBLE) AS cogs_goods_primary,
       r.cogs_source,
       CAST(r.qty_sapo           AS DOUBLE) AS qty_sapo,
       (p.order_code IS NOT NULL) AS is_promo, p.is_gift_no_invoice
FROM int_order_cogs_reconciled r
LEFT JOIN int_order_promo_goods_cost p
    ON r.order_code = p.order_code AND r.sku = p.sku
WHERE r.order_code = ?
ORDER BY COALESCE(p.order_code IS NOT NULL, FALSE), r.sku
"""
