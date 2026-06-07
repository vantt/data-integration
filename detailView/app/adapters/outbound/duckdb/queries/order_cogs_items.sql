-- Per-SKU COGS breakdown for one order.
-- Grain: (order_code, sku) from int_order_cogs_reconciled.
-- Keyed by order_code (recon table has no order_id FK).
-- LEFT JOIN int_order_promo_goods_cost to flag gift lines (line_revenue = 0).
SELECT
    r.sku,
    r.variant_id,
    r.cogs_goods_sapo,
    r.cogs_goods_misa,
    r.cogs_goods_primary,
    r.cogs_source,
    r.qty_sapo,
    (p.order_code IS NOT NULL)  AS is_promo,
    p.is_gift_no_invoice
FROM int_order_cogs_reconciled r
LEFT JOIN int_order_promo_goods_cost p
    ON r.order_code = p.order_code AND r.sku = p.sku
WHERE r.order_code = ?
ORDER BY COALESCE(p.order_code IS NOT NULL, FALSE), r.sku;
