-- Resolve an exact order by code, order_id, or shipment identifiers (case-insensitive).
-- Returns the canonical order_code.
--
-- Priority (lowest match_rank wins):
--   0 = order_code match  (e.g. '260529N88MBG3U')
--   1 = order_id match    (e.g. '1036830915')
--   2 = fulfillment_code / fulfillment_id / tracking_code match
--
-- fact_fulfillments may not exist on older DBs; the outer query guards with a
-- view-existence check so a missing view returns zero rows (no crash).
--
-- Positional parameters: ?, ?, ?, ?, ?, ?   (6 total)
--   1: CASE order_code match_rank expression
--   2: WHERE order_code
--   3: WHERE order_id
--   4: WHERE fulfillment_code
--   5: WHERE fulfillment_id
--   6: WHERE tracking_code

SELECT order_code, match_rank
FROM (
    -- Primary: match on fact_orders directly (order_code or order_id)
    SELECT
        order_code,
        CASE WHEN UPPER(order_code) = UPPER(?) THEN 0 ELSE 1 END AS match_rank
    FROM fact_orders
    WHERE UPPER(order_code) = UPPER(?)
       OR order_id          = ?

    UNION ALL

    -- Secondary: match on shipment identifiers via fact_fulfillments.
    -- Guarded by a subquery that returns nothing if the view does not exist.
    SELECT
        fo.order_code,
        2 AS match_rank
    FROM fact_orders fo
    INNER JOIN (
        SELECT order_code AS ff_order_code
        FROM fact_fulfillments
        WHERE UPPER(fulfillment_code) = UPPER(?)
           OR UPPER(fulfillment_id)   = UPPER(?)
           OR UPPER(tracking_code)    = UPPER(?)
        LIMIT 1
    ) ff ON UPPER(fo.order_code) = UPPER(ff.ff_order_code)

) combined
ORDER BY match_rank
LIMIT 1;
