-- =================================================================================================
-- SINGULAR TEST: NO PROMO IN OVERHEAD COSTS
-- =================================================================================================
-- Invariant: fact_order_costs must NEVER contain rows where cost_category='OVERHEAD'
-- and cost_type indicates a promo cost (cost_type LIKE '%promo%').
--
-- Promo goods cost rows (cost_type='promo_goods_cost', cost_category='PROMO_GOODS') are
-- legitimate. The violation is when a promo cost leaks into the OVERHEAD category, which
-- would mean account 64214 (or a similar promo account) was NOT dropped from the pool.
--
-- Returns offending rows — test FAILS if any rows are returned.
-- =================================================================================================

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    amount
FROM {{ ref('fact_order_costs') }}
WHERE cost_category = 'OVERHEAD'
  AND cost_type LIKE '%promo%'
