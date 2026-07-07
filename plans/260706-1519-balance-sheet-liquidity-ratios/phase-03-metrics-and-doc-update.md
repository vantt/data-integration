# Phase 3 — Metrics + Domain Doc Update

**Depends on:** phase-02 (`fact_balance_sheet_monthly` live and sign-verified)
**Blocks:** phase-04

## Context

`docs/analytics-handbook/domains/finance.md` § "Context: Balance Sheet & Liquidity — Planned" (metrics #16-18) currently marks Current Ratio, Quick Ratio, and DSO as `Status: Planned — fact_account_balances not yet built`. This phase rewrites that section with real formulas against `fact_balance_sheet_monthly`, per the doc's own convention (dbt Source header, SQL logic block, Status line) used by every other context in the file.

## DSO revenue source decision (corrected 2026-07-06 per user)

**Use MISA, not Sapo, for `Annual_Revenue`.** Domain correction from user: Sapo's completeness/accuracy advantage is narrowly scoped to **COGS of goods sold** (per-order product cost) — it is NOT the authoritative source for company-wide revenue totals. For anything requiring full-company completeness (a balance-sheet-grade ratio like DSO), MISA is the source. This refines `[[project_misa_channel_mostly_unknown]]` (that memory's table covers channel/order-cost/overhead — it doesn't cover "which source is complete for total revenue"; MISA is now the answer for that specific need).

`Accounts_Receivable` = `fact_balance_sheet_monthly.trade_receivables` (MISA, account 131). `Annual_Revenue` = trailing-12-month **revenue booked in MISA GL class-5 accounts** (511x — Doanh thu bán hàng hóa/cung cấp dịch vụ/khác), NOT `fact_orders.net_revenue` (Sapo). Source it from `fact_account_balance_monthly.period_credit` for `account_code LIKE '511%'` — `period_credit` is already the raw monthly credit total (a flow, not a running balance), so **no sign flip needed** here (unlike `closing_balance`, which is a net position and does need the phase-01/02 sign correction). Sum `period_credit` across all 511x sub-accounts per period_month, then take a trailing-12-month rolling sum.

Caveat to verify in phase-01/02 validation: MISA's full-ledger backfill only starts 2026-01 (per `plan.md`), so a true trailing-12-month MISA revenue window isn't available until ~2027-01. Until then, either (a) show DSO only once 12 months of MISA revenue exist, or (b) annualize a shorter window (e.g. `trailing_N_months * 12/N`) with a caveat flag — pick (b) for early months so the metric isn't blank for a year, and label it clearly as "annualized from N months" in the tooltip/card subtitle.

## Doc edit

Replace the "Context: Balance Sheet & Liquidity — Planned" section (currently around line 460-524 in `finance.md` — line numbers may have shifted after the phase-0-onward Cash Flow section cleanup; search for the heading text) with:

- Header: drop "— Planned" suffix once live; update `> **Status:**` line to reference `fact_balance_sheet_monthly` (phase-02, available) instead of "not yet built".
- `dbt Source:` → [`fact_balance_sheet_monthly`](../../../transformation/models/marts/finance/fact_balance_sheet_monthly.sql)
- Metric #16 Current Ratio:
  ```sql
  SELECT period_month, current_assets * 1.0 / NULLIF(current_liabilities, 0) AS current_ratio
  FROM fact_balance_sheet_monthly
  ```
  Status: Available.
- Metric #17 Quick Ratio:
  ```sql
  SELECT period_month,
         (current_assets - inventory_value) * 1.0 / NULLIF(current_liabilities, 0) AS quick_ratio
  FROM fact_balance_sheet_monthly
  ```
  Status: Available.
- Metric #18 DSO:
  ```sql
  WITH misa_revenue AS (
      SELECT period_month, SUM(period_credit) AS revenue
      FROM fact_account_balance_monthly
      WHERE account_code LIKE '511%'
      GROUP BY period_month
  ),
  trailing AS (
      SELECT
          period_month,
          SUM(revenue) OVER (ORDER BY period_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS trailing_revenue,
          COUNT(*)     OVER (ORDER BY period_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS months_in_window
      FROM misa_revenue
  )
  SELECT
      b.period_month,
      b.trade_receivables * 365.0
        / NULLIF(t.trailing_revenue * 12.0 / t.months_in_window, 0) AS dso_days,  -- annualized if window < 12mo
      t.months_in_window
  FROM fact_balance_sheet_monthly b
  JOIN trailing t ON t.period_month = b.period_month
  ```
  Status: Available (caveat: annualized from a shorter window until MISA full-ledger revenue history reaches 12 months, ~2027-01 — see "DSO revenue source decision" above; surface `months_in_window` on the card so it's clear early values are annualized, not a true trailing-12mo).
- Update the "Context Overview" table row: `Data Ready` column → `fact_balance_sheet_monthly` (phase-02); `Needs Added` → "None" (was "Source/model implementation required").
- Update `Q1. ... Readiness` "Tradeoffs / Caveats" bullet to mention the Jan-2026 trend-start limitation (see plan.md).

## Validation

- Re-read the edited section once done; confirm no other part of `finance.md` still references `fact_account_balances` as a future/planned dependency (grep for it) — if any Related Metrics table elsewhere lists these metrics as blocked on it, update those too.
- Confirm metric numbering (#16-18) doesn't collide with anything renumbered by the earlier Cash Flow section cleanup (it shouldn't — that removed metric #19 entirely, not 16-18).

## Files touched

- `docs/analytics-handbook/domains/finance.md` (edit § Balance Sheet & Liquidity)
