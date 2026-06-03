-- Cost-ledger rows for one order (grain: 1 row per cost_type), joined on order_id.
SELECT
    cost_type,
    cost_category,
    amount,
    discount_rate,
    discount_type,
    source_system,
    source_record,
    fee_source
FROM fact_order_costs
WHERE order_id = ?
ORDER BY cost_category, cost_type;
