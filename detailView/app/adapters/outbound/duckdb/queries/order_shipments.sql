-- Shipment legs for one order from fact_fulfillments (grain: 1 row per shipment).
-- Joined on order_code (VARCHAR) — consistent with order_returns which also uses order_code.
-- NULL shipped_at rows sort last; ties broken by created_at ascending.
SELECT
    fulfillment_id,
    fulfillment_code,
    tracking_code,
    carrier_id,
    shipping_service,
    status,
    cod_amount,
    created_at,
    shipped_at
FROM fact_fulfillments
WHERE UPPER(order_code) = UPPER(?)
ORDER BY shipped_at NULLS LAST, created_at;
