# Plan: Full GL / Accounting Entries

> Created: 2026-06-09
> **Status: SUPERSEDED (2026-07-07)** — remaining scope moved to
> `plans/260706-1519-balance-sheet-liquidity-ratios/plan.md` Phase 5 ("Absorbed scope: Full P&L").
> This plan is now closed/archived; do not implement from here, go to Phase 5 in that plan instead.
> Origin: `analytics_improvement_opportunities.md` § Full GL / Accounting Entries
> (updated 2026-06-24: untouched by 260623 audit work; no GL extract or fact_gl_entries yet)
> (updated 2026-07-07: re-checked against current code. `260702-1727-misa-cashflow-budget-planner`
> (commit `91c6039d`, 2026-07-03) built full-chart-of-accounts ingestion + a self-populating
> `dim_gl_account` + `fact_account_balance_monthly` as infrastructure for its own cashflow/budget
> scope — this happens to satisfy most of this plan's "data needed" prerequisites, undocumented
> here until now. Remaining open items (P&L category flags, fact_gl_entries mart decision, Net
> Profit/EBITDA card, GL-vs-orders reconciliation) moved to
> `plans/260706-1519-balance-sheet-liquidity-ratios/plan.md` Phase 5 rather than re-litigated here,
> since that plan already owns the same `dim_gl_account`/`fact_account_balance_monthly` infra and
> is active. `docs/analytics-handbook/domains/finance.md` correctly still marks Net Margin %/EBITDA
> "Planned" — that flips to "Available" only once Phase 5 there ships.)

## Objective

Ingest general ledger entries from accounting system to build full company P&L beyond gross/channel profitability.

## What this unlocks

- Full P&L statement (revenue → COGS → gross profit → OpEx → operating margin → net margin)
- EBITDA
- OpEx by category (salaries, rent, marketing overhead, depreciation)
- Department / cost-center profitability
- Accounting reconciliation between operational revenue and GL

## Data needed

- `fact_gl_entries` from MISA AMIS (or equivalent)
- Chart of accounts with category mapping: revenue, COGS, OpEx, tax, interest, depreciation
- Per entry: account, debit amount, credit amount, posting date, voucher/document number
- Optional: cost center, department, channel, branch

## Current state (re-verified 2026-07-07)

- **`fact_gl_entries` (named mart) still does not exist**, BUT `src_misa_account_ledger` staging
  model (transaction grain: account, voucher_no, posting_date, offset_account, debit, credit) now
  covers the FULL chart of accounts, not just 642x — functionally equivalent data, just not
  promoted to a mart with its own schema tests/rolling export.
- Finance domain (`finance.md` §12 Net Margin %, §13 EBITDA) still correctly marks these "Planned".
- **Superseded assumption:** "MISA account_ledger pipeline already handles overhead accounts
  (6421/6422)" — as of `260702-1727-misa-cashflow-budget-planner` (2026-07-03), the downloader
  defaults to `--all-accounts` (full chart of accounts) for the Dagster job; 642x-only was the OLD
  state this plan was written against.
- Previously "unclassified" accounts (`64217`, `64212` family) now get a real classification via
  `dim_gl_account.account_class`/`cashflow_line` (self-populating from whatever appears in the ledger).

## What already exists (built for cashflow, reusable here)
- `transformation/models/marts/core/dim_gl_account.sql` — self-populating chart of accounts,
  `account_class` (VAS first-digit: 1 asset, 2 fixed asset, 3 liability, 4 equity, 5 revenue,
  6 COGS+OpEx combined, 7 other income, 8 other expense) + `cashflow_line` (thu/chi bucket, not
  P&L category).
- `transformation/models/marts/finance/fact_account_balance_monthly.sql` — grain (account_code,
  period_month): opening/period_debit/period_credit/closing balance for every account. Finer than
  the originally-planned (account_category, period_month) grain — rolls up fine, just needs a
  category-level aggregation on top.
- `transformation/models/marts/finance/fact_cash_movement.sql` — line-grain cash flows (111/112).

## Implementation steps

- [x] Define GL extract contract — done via `--all-accounts` downloader flag (260702 plan)
- [~] Map chart of accounts to categories — `account_class` gives VAS 1-9 split, but 6 lumps
  COGS (632) and OpEx (641/642) together; need a sub-range split for a real P&L, not just cashflow buckets
- [x] Extend parser for full GL scope — done (260702 plan): `--all-accounts`, running/opening balance capture
- [~] `fact_gl_entries` mart — data exists at the right grain in `src_misa_account_ledger`
  (staging layer), but not promoted to a tested/exported mart. Low effort to close if still wanted
  as a named artifact; may be YAGNI if `fact_account_balance_monthly` already covers reporting needs.
- [x] `int_gl_monthly_summary`-equivalent — `fact_account_balance_monthly` (account_code, not
  account_category grain — finer, roll up in the P&L query itself)
- [ ] Add "Net Profit" / full-company P&L card to Finance dashboard — still not built
- [ ] Reconcile GL revenue (511%/515%/71%) vs `fact_orders.net_revenue` — still not built

## Dependency

Blocks: full net margin reporting, EBITDA, department P&L.
Does not block: gross profit, channel net profit (already available via `fact_order_economics`).
