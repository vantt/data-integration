{{ config(
    tags=['int', 'cogs', 'promo', 'overhead-dedup'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: PROMO 642 MONTHLY TOTAL
-- =================================================================================================
-- Grain:   period_month — one row per calendar month
-- Purpose: Reconciliation/monitoring view of MISA sales-ledger TK642 promo outflows.
--          MONITORING/AUDIT ONLY — not referenced by any downstream mart model.
--
-- How promo exclusion actually works (corrected 2026-06-05):
--   Promo account 64214 is excluded from the overhead pool via its classification
--   treatment (`drop_promo_count_once`) in stg_overhead_account_classification.
--   int_overhead_pool_monthly filters to `treatment LIKE 'keep_%'`, so 64214 never
--   enters the pool. This is a classification-based exclusion, NOT a subtraction.
--   This model is NOT subtracted from any pool and is NOT called by any dbt model.
--
-- Known gap: standalone XK-voucher promo (no matching Sapo order) is not captured in
--   P&L waterfall (~40M/year in 2026). Accepted business limitation — documented in
--   docs/architecture/order-pl/overhead-allocation-and-classification-guide.md.
--
-- Source:  std_misa_sales_lines TK642 lines — full history by MISA posting_date.
--          NOT scoped to rolling window (needed for full overhead reconciliation).
--
-- Validation: SUM(sales_ledger_642_amount) across all periods = 1,076,303,444.
-- NOTE: Audit/recon only — do NOT build Metabase cards on this model.
-- =================================================================================================

SELECT
    DATE_TRUNC('month', posting_date::DATE)  AS period_month,
    SUM(cogs_amount)                         AS sales_ledger_642_amount,
    COUNT(*)                                 AS line_count
FROM {{ ref('std_misa_sales_lines') }}
WHERE cost_account_group = '642'
GROUP BY 1
ORDER BY 1
