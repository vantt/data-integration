-- Resolve an exact order by code OR id (case-insensitive). Returns the canonical order_code.
--
-- Priority: order_code match wins over order_id match so that a code like "1036830915"
-- (if it happened to equal an order_code) is handled correctly. In practice, order_ids
-- are pure numeric strings while order_codes are alphanumeric, so there is no ambiguity.
--
-- Single parameter (?) used twice via the DuckDB positional placeholder.
SELECT order_code,
       CASE WHEN UPPER(order_code) = UPPER(?) THEN 0 ELSE 1 END AS match_rank
FROM   fact_orders
WHERE  UPPER(order_code) = UPPER(?)
   OR  order_id          = ?
ORDER  BY match_rank
LIMIT  1;
