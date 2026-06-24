# Plan: Full GL / Accounting Entries

> Created: 2026-06-09
> Status: ❌ Not started
> Origin: `analytics_improvement_opportunities.md` § Full GL / Accounting Entries
> (updated 2026-06-24: untouched by 260623 audit work; no GL extract or fact_gl_entries yet)

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

## Current state

- `fact_gl_entries` does not exist
- Finance domain marks GL-based metrics as planned
- **Related work:** MISA `account_ledger` pipeline already handles overhead accounts (6421/6422) — same parser and ingestion pattern applies; see `docs/architecture/order-pl/overhead-account-ledger-ingestion-design.md`
- Unclassified accounts in current ledger that may relate: `64217` (31.5B net, 2025), `64212` family (negative net, 2025)

## Implementation steps

- [ ] Define GL extract contract with finance team (which accounts, which periods)
- [ ] Map chart of accounts to categories (revenue / COGS / OpEx / tax / depreciation)
- [ ] Extend `account-ledger-parser.py` or create new parser for full GL scope (not just 642x)
- [ ] Create `fact_gl_entries` mart with grain: (account, voucher_no, posting_date)
- [ ] Create `int_gl_monthly_summary` aggregated by (account_category, period_month)
- [ ] Add "Net Profit" card to Finance P&L dashboard — mark unavailable until this is done
- [ ] Reconcile GL revenue vs `fact_orders` net_revenue

## Dependency

Blocks: full net margin reporting, EBITDA, department P&L.
Does not block: gross profit, channel net profit (already available via `fact_order_economics`).
