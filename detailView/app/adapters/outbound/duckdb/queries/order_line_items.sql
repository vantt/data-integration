-- Line items for one order: fact_sales x dim_products (by product_key), joined on order_id.
-- NOTE: per-line US price lives only in int_us_shipment_line_prices, an int_* model that
-- the read-only serving contract forbids querying. So LineItem.us_price_incl_vat stays None.
SELECT
    fs.order_line_id,
    dp.sku,
    dp.product_name,
    dp.variant_name,
    dp.brand_name,
    dp.category,
    dp.unit,
    fs.quantity,
    fs.revenue,
    fs.discount_amount,
    fs.distributed_discount_amount,
    fs.weight_grams
FROM fact_sales fs
LEFT JOIN dim_products dp ON fs.product_key = dp.product_key
WHERE fs.order_id = ?
ORDER BY fs.order_line_id;
