{{ config(
    tags=['int', 'cogs', 'promo', 'overhead-dedup'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: PROMO 642 MONTHLY TOTAL
-- =================================================================================================
-- Grain:   period_month — one row per calendar month
-- Purpose: Per-period sales-ledger TK642 total for phase-04 overhead dedup.
--          Phase-04 subtracts this amount from the overhead expense pool to avoid
--          double-counting (count-once: promo goods cost already captured in
--          int_order_promo_goods_cost; should NOT also appear in overhead pool).
--
-- Source:  std_misa_sales_lines TK642 lines — full history by MISA posting_date.
--          NOT scoped to rolling window (needed for full overhead reconciliation).
--
-- Validation: SUM(sales_ledger_642_amount) across all periods = 1,076,303,444.
-- NOTE: Dedup helper only — do NOT build Metabase cards on this model.
-- =================================================================================================

SELECT
    DATE_TRUNC('month', posting_date::DATE)  AS period_month,
    SUM(cogs_amount)                         AS sales_ledger_642_amount,
    COUNT(*)                                 AS line_count
FROM {{ ref('std_misa_sales_lines') }}
WHERE cost_account_group = '642'
GROUP BY 1
ORDER BY 1
