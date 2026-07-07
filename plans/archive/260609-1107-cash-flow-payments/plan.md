# Plan: Cash Flow and Liquidity

> Created: 2026-06-09
> **Status: Superseded** (closed 2026-07-06 — treasury/cash-flow objective was delivered via a different route; see below)
> Origin: `analytics_improvement_opportunities.md` § Cash Flow and Liquidity

## Objective (original)

Move from sales/payment reporting to treasury visibility — cash balance, daily movement, DSO, short-term liquidity.

## Why superseded

This plan assumed Sapo payment records (`fact_payments`) would be the source for treasury cash flow. In practice the company's real cash ledger lives in **MISA** (111/112 accounts), not Sapo, so `plans/260702-1727-misa-cashflow-budget-planner/` built the actual Cashflow dashboard from a MISA GL-based pipeline instead (`fact_cash_movement`, `fact_account_balance_monthly`, Metabase dashboard #113/#114), then closed the operational gaps on top of it as later phases (originally a separate `260705-1459-budget-cashflow-workable-loop` plan, merged in 2026-07-07). Done.

## Verified final state (2026-07-06)

- ✅ **Cash Flow dashboard** — done, but via MISA route, not Sapo/`fact_payments`. Metabase "Finance Cashflow" (#113) + "Finance Budget vs Actual" (#114), see `plans/260702-1727-misa-cashflow-budget-planner/`.
- ✅ **Daily cash inflow/outflow, running balance** — done via `fact_cash_movement` (CF1-CF4 in `docs/analytics-handbook/domains/finance.md` § Cashflow (Dòng tiền vận hành)).
- ⚠️ **Bank/account balance snapshots** — done but **monthly**, not daily (`fact_account_balance_monthly`), and MISA-sourced not bank-export-sourced. Sufficient for current use.
- ❌ **DSO (days sales outstanding) / AR aging** — still NOT built anywhere. Documented as "Planned" in `docs/analytics-handbook/domains/finance.md` (metrics #16-18, needs `fact_account_balances`). Carried forward as part of `plans/260609-1107-b2b-credit-terms/` (customer-level DSO, credit exposure) — that plan is separately tracked, not started.
- ❌ **Link to B2B outstanding (fact_orders unpaid → AR proxy)** — not done here; same fate, folded into `plans/260609-1107-b2b-credit-terms/` objective/dependency.
- ✅ `fact_payments` itself — populated (9,272 rows, commit 8624772) and **still actively used**, but for order-level payment status in CRM/detailView (`customer_orders_sql.py`, `order_payments.sql`, `int_customer_metrics.sql`), not for the treasury dashboard this plan targeted.

## Stale doc note (not fixed here)

`docs/analytics-handbook/domains/finance.md` still has an old "Context: Cash Flow" section (single metric, Net Cash Flow, sourced from `fact_payments`, with a `type='inflow'/'outflow'` column that doesn't exist in the model) — superseded by the newer "Context: Cashflow (Dòng tiền vận hành)" section (CF1-CF7, `fact_cash_movement`-based). Left as-is; flag for cleanup if someone touches that doc next.

## Dependency

Remaining DSO/AR-aging scope lives in `plans/260609-1107-b2b-credit-terms/` (not started) — no ingestion or model changes needed here.
