-- A customer's order history (newest-first, capped by LIMIT in the repo).
-- fact_orders x economics x dim_channels x dim_staff(seller). payment_label is the first
-- payment method seen for the order; has_return from economics flag.
SELECT
    fo.order_code,
    fo.order_timestamp                          AS order_date,
    fo.status,
    ch.channel_name,
    seller.full_name                            AS seller_name,
    fo.total_collected,
    foe.gross_profit,
    foe.gross_margin_pct,
    foe.carrier_id,
    COALESCE(foe.has_returns, FALSE)            AS has_return,
    (
        SELECT pm.payment_method_name
        FROM fact_payments fp
        LEFT JOIN dim_payment_methods pm ON fp.payment_method_key = pm.payment_method_key
        WHERE fp.order_id = fo.order_id
        ORDER BY fp.payment_timestamp
        LIMIT 1
    )                                           AS payment_label
FROM fact_orders fo
LEFT JOIN fact_order_economics foe ON fo.order_id = foe.order_id
LEFT JOIN dim_channels ch          ON fo.channel_key = ch.channel_key
LEFT JOIN dim_staff seller         ON fo.seller_staff_key = seller.staff_key
WHERE fo.customer_key = ?
ORDER BY fo.order_timestamp DESC NULLS LAST
LIMIT ?;
