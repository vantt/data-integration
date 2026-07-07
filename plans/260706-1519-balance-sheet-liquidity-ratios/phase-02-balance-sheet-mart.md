# Phase 2 — Balance Sheet Mart

**Depends on:** phase-01 (classification flags on `dim_gl_account`)
**Blocks:** phase-03

## Context

`fact_account_balance_monthly` has one row per (account_code, period_month) with `opening_balance` and `closing_balance = debit_balance - credit_balance`. This phase aggregates it into one row per `period_month` with the totals liquidity ratios need — **with the sign correction from phase-01 applied**, since `closing_balance` is negative for credit-normal accounts (liabilities/equity/revenue) in their normal position.

## New model: `transformation/models/marts/finance/fact_balance_sheet_monthly.sql`

```sql
{{ config(
    tags=['mart', 'fact', 'misa', 'finance'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: BALANCE SHEET MONTHLY
-- =================================================================================================
-- Grain: 1 row per period_month. Aggregates fact_account_balance_monthly x dim_gl_account into
-- the totals Current Ratio / Quick Ratio / DSO need.
--
-- Sign correction: fact_account_balance_monthly.closing_balance = debit_balance - credit_balance,
-- which is positive-normal only for debit-normal accounts (assets). Credit-normal accounts
-- (liabilities/equity/revenue) show a NEGATIVE closing_balance in their normal position — flip
-- sign via dim_gl_account.normal_balance_side before summing, or totals come out wrong/negative.
--
-- Only classes 1-4 (assets/liabilities/equity) are in scope; 5/6/7/8 (P&L accounts) excluded —
-- that's fact_order_costs / GL P&L territory, not balance sheet.
-- =================================================================================================

WITH balances AS (
    SELECT
        b.period_month,
        b.account_code,
        b.closing_balance,
        d.normal_balance_side,
        d.is_current_asset,
        d.is_non_current_asset,
        d.is_current_liability,
        d.is_non_current_liability,
        d.is_equity,
        d.is_inventory,
        d.is_trade_receivable,
        d.is_cash,
        -- flip sign so every balance is positive in its own normal direction
        CASE
            WHEN d.normal_balance_side = 'credit' THEN -b.closing_balance
            ELSE b.closing_balance
        END AS normalized_balance
    FROM {{ ref('fact_account_balance_monthly') }} b
    LEFT JOIN {{ ref('dim_gl_account') }} d ON d.account_code = b.account_code
    WHERE b.closing_balance IS NOT NULL  -- pre-full-ledger 642-only partitions have NULL here
      AND d.normal_balance_side IS NOT NULL  -- exclude unclassified/garbage-code rows defensively
)

SELECT
    period_month,
    SUM(CASE WHEN is_current_asset THEN normalized_balance ELSE 0 END)         AS current_assets,
    SUM(CASE WHEN is_non_current_asset THEN normalized_balance ELSE 0 END)     AS non_current_assets,
    SUM(CASE WHEN is_current_liability THEN normalized_balance ELSE 0 END)     AS current_liabilities,
    SUM(CASE WHEN is_non_current_liability THEN normalized_balance ELSE 0 END) AS non_current_liabilities,
    SUM(CASE WHEN is_equity THEN normalized_balance ELSE 0 END)                AS equity,
    SUM(CASE WHEN is_cash THEN normalized_balance ELSE 0 END)                  AS cash_and_equivalents,
    SUM(CASE WHEN is_inventory THEN normalized_balance ELSE 0 END)             AS inventory_value,
    SUM(CASE WHEN is_trade_receivable THEN normalized_balance ELSE 0 END)      AS trade_receivables,
    'misa' AS source_system
FROM balances
GROUP BY period_month
```

## Validation (do this before phase-03 touches any docs)

1. `dbt build --select fact_balance_sheet_monthly`.
2. **Sign spot-check (critical):** query June 2026 — `current_liabilities` must be **positive** and roughly match `ABS(-952,249,104)` for account `331` alone (plus the other current-liability accounts). If it comes out negative, the `normal_balance_side` flip is backwards — fix before proceeding.
3. **Balance-check dbt test:** `total_assets` (`current_assets + non_current_assets`) vs `total_liabilities_and_equity` (`current_liabilities + non_current_liabilities + equity`) per period_month. Expect these to be *close* but not necessarily exact — some class-5/6/7/8 P&L accounts feed into retained earnings (421x) in a real close process, which this simple aggregation doesn't simulate. Pick a tolerance (e.g. flag if drift > some % of total_assets) and document it as a known approximation, not a hard equality assertion — this is a monitoring signal for finance, not a GAAP-audited balance sheet.
4. Confirm row count = number of distinct `period_month` in `fact_account_balance_monthly` where `closing_balance IS NOT NULL` (i.e., 2026-01 onward — pre-2026 rows are all-NULL from the 642-only era and correctly excluded).

## Deploy

Same 2-step as any new mart consumed by Metabase (see `feedback_duckdb_view_rebuild` / `feedback_new_mart_crm_serving_integration` project memory):
1. `dbt build --select fact_balance_sheet_monthly` inside `data_platform` container.
2. Stop Metabase, run `python -m scripts.bootstrap_serving_views` (or equivalent already used for `fact_account_balance_monthly`/`fact_cash_movement`), restart Metabase.

## Files touched

- `transformation/models/marts/finance/fact_balance_sheet_monthly.sql` (new)
- `transformation/models/marts/finance/schema.yml` (add model + column docs + the balance-check test)
