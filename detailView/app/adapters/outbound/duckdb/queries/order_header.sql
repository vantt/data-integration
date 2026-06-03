-- Single-order header + economics + dims, anchored on fact_orders by order_code.
-- Case-insensitive match. order_id is VARCHAR in the serving layer; cast handled in Python.
-- US revenue (fact_us_shipment_economics) LEFT JOINed on order_id.
SELECT
    fo.order_id,
    fo.order_code,
    fo.customer_key,
    fo.status,
    fo.payment_status,
    fo.fulfillment_status,
    fo.order_timestamp                          AS created_at,
    fo.first_shipped_at,
    fo.updated_at,
    fo.time_to_complete_hours,
    fo.shipping_address,
    fo.max_discount_rate,
    fo.primary_discount_type,
    -- domestic revenue waterfall
    fo.gross_revenue,
    fo.discount_amount,
    fo.net_revenue,
    fo.tax_amount,
    fo.total_collected,
    -- economics (P&L) — LEFT JOIN: may be absent
    foe.cogs_amount,
    foe.gross_profit,
    foe.gross_margin_pct,
    foe.channel_net_profit,
    foe.channel_net_margin_pct,
    foe.shopee_platform_fees,
    foe.shopee_infra_fee,
    foe.shopee_voucher_xtra_fee,
    foe.shopee_taxes,
    foe.shopee_net_settlement,
    foe.cod_amount,
    foe.carrier_id,
    foe.return_amount,
    foe.return_count,
    foe.has_cogs,
    foe.has_platform_fees,
    foe.has_returns,
    -- US CrossBorder economics — LEFT JOIN: present only for US orders
    us.total_us_revenue_excl_vat,
    us.total_us_revenue_incl_vat,
    us.line_item_count                          AS us_line_item_count,
    us.has_unpriced_sku,
    us.unpriced_sku_count,
    (us.order_id IS NOT NULL)                   AS is_us,
    -- channel
    ch.channel_name, ch.channel_code, ch.channel_category, ch.channel_format,
    ch.platform, ch.channel_brand, ch.market,
    -- promotion (first promo code only — see researcher-01 caveat)
    pr.promotion_code,
    -- staff (seller primary, creator fallback)
    seller.full_name                            AS seller_name,
    seller.email                                AS seller_email,
    creator.full_name                           AS creator_name,
    tm.team_name,
    bl.branch_location_name                     AS branch_name,
    -- shipping geography
    geo.province, geo.district, geo.ward, geo.country,
    -- customer ref
    cust.customer_id                            AS cust_customer_id,
    cust.full_name                              AS cust_full_name,
    cust.customer_type                          AS cust_customer_type,
    cust.value_group                            AS cust_value_group,
    cust.lifetime_value                         AS cust_lifetime_value
FROM fact_orders fo
LEFT JOIN fact_order_economics foe   ON fo.order_id = foe.order_id
LEFT JOIN fact_us_shipment_economics us ON fo.order_id = us.order_id
LEFT JOIN dim_channels ch            ON fo.channel_key = ch.channel_key
LEFT JOIN dim_promotions pr          ON fo.promotion_key = pr.promotion_key
LEFT JOIN dim_staff seller           ON fo.seller_staff_key = seller.staff_key
LEFT JOIN dim_staff creator          ON fo.creator_staff_key = creator.staff_key
LEFT JOIN dim_teams tm               ON fo.team_key = tm.team_key
LEFT JOIN dim_branch_location bl     ON fo.branch_location_key = bl.branch_location_key
LEFT JOIN dim_geography geo          ON fo.shipping_geography_key = geo.geography_key
LEFT JOIN dim_customers cust         ON fo.customer_key = cust.customer_key
WHERE UPPER(fo.order_code) = UPPER(?)
LIMIT 1;
