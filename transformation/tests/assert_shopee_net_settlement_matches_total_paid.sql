-- Reconciliation invariant: int_shopee_order_fees.net_settlement
-- MUST equal the source column int_shopee_order_fees.total_paid_amount.
--
-- Rationale: "Tổng tiền đã thanh toán" (total_paid_amount) in the Shopee
-- Income Released report IS Shopee's per-order net payout. It already has
-- fees, discounts, and taxes embedded. Recomputing net_settlement from
-- components (as a prior formula did) double-counts and drifts the mart
-- from the Summary sheet "Tổng số tiền" checksum.
--
-- This test fails if a future change ever re-introduces a derived formula.

SELECT
    order_code,
    net_settlement,
    total_paid_amount,
    net_settlement - total_paid_amount AS diff
FROM {{ ref('int_shopee_order_fees') }}
WHERE net_settlement <> total_paid_amount
