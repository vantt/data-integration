# Balance Sheet & Liquidity Ratios (Current Ratio, Quick Ratio, DSO)

**Status:** Not started
**Created:** 2026-07-06
**Origin:** gap found while auditing `plans/archive/260609-1107-cash-flow-payments/` — `docs/analytics-handbook/domains/finance.md` metrics #16-18 (Current Ratio, Quick Ratio, company-wide DSO) marked "Planned — `fact_account_balances` not yet built" and not covered by any other active plan (`plans/260609-1107-b2b-credit-terms/` only covers customer-level AR aging, not full balance sheet).

## Objective

Build company-wide liquidity ratios (Current Ratio, Quick Ratio, DSO) from the MISA full-ledger data already ingested by `plans/archive/260707-1207-misa-gl-infrastructure/` (split 2026-07-07 out of `plans/archive/260702-1727-misa-cashflow-budget-planner/`, itself archived DONE 2026-07-07).

## Key finding — most of the data already exists

`fact_account_balance_monthly` (grain: account_code × period_month, built in the MISA cashflow plan) already carries **opening/closing balance for every account in the ledger**, not just cash. Verified live on `olap.duckdb` 2026-07-06:

- 67 distinct accounts with real posting activity, spanning class 1 (current assets: 111x/112x cash, 131 AR, 1331 VAT input, 1386/13888 other receivable, 141 advances, 156/157 inventory), class 2 (2421/2422 — long-term prepaid expense, non-current), class 3 (331 AP, 3335/3341/3348 payroll+tax, 33682/3383/3384/3385/33881 insurance/other payable — **all current, zero long-term debt observed**), class 4 (equity: 4111/4211/4212), class 5 (revenue), 6/8 (expense).
- Coverage: only ~12-15 accounts/month tracked Jan-Dec 2025 (642-only, pre-full-ledger), jumping to 36-39 accounts/month from **2026-01 onward** (post full-ledger backfill). → balance-sheet ratios can only trend from **Jan 2026**, not earlier. Document as a known limitation, not a blocker.
- `dim_gl_account.account_class` = `LEFT(account_code, 1)` already exists but is unrefined (no current/non-current split) and the dim table's account UNIVERSE (which unions `account` + `offset_account`) contains garbage numeric "codes" (7-10 digit numbers that are clearly leaked amounts, not real VAS codes) coming from unparseable multi-line `offset_account` entries — **confirmed these never leak into `fact_account_balance_monthly.account_code`** (checked: 0 rows with `LENGTH(account_code) > 6`), so the fact table is clean; only `dim_gl_account`'s broader universe needs a defensive filter.

## Critical correctness risk — sign convention

`fact_account_balance_monthly.closing_balance = debit_balance - credit_balance` (same formula as `fact_cash_movement.running_balance`). This is correct for debit-normal accounts (assets, class 1/2) but **inverts sign for credit-normal accounts** (liabilities class 3, equity class 4, revenue class 5). Verified live: account `331` (Phải trả người bán, a liability) shows `closing_balance = -952,249,104` for June 2026 — negative, because credit > debit is normal for a payable. Any aggregation into "Total Current Liabilities" **must flip sign** (multiply by -1, or take ABS) for class-3/4/5 accounts before summing, or liquidity ratios will be silently wrong (denominator negative or assets/liabilities miscounted). This is the single most important thing to get right in Phase 2.

## Phases

| # | Phase | File | Ra được gì |
|---|-------|------|-----------|
| 1 | Chart-of-account classification | `phase-01-account-classification.md` | `dim_gl_account` gets `is_current_asset`, `is_non_current_asset`, `is_current_liability`, `is_non_current_liability`, `is_equity`, `is_inventory`, `is_trade_receivable`, `normal_balance_side` flags; garbage-code filter; dbt test |
| 2 | Balance sheet mart | `phase-02-balance-sheet-mart.md` | `fact_balance_sheet_monthly` (grain: period_month) with sign-corrected current_assets/current_liabilities/inventory/trade_receivables/equity; balance-check dbt test |
| 3 | Metrics + domain doc | `phase-03-metrics-and-doc-update.md` | `finance.md` #16-18 flipped from "Planned" to real SQL/Data Ready; DSO wired to `fact_orders` trailing-12mo net_revenue |
| 4 | Dashboard | `phase-04-dashboard-deploy.md` | New "Balance Sheet & Liquidity" tab on Metabase dashboard #113 (Finance Cashflow) — 3 scorecards + trend |
| 5 | Full P&L rollup (deferred, absorbed from `plans/archive/260609-1107-gl-accounting-entries/`) | not yet detailed | See "Absorbed scope" below |

Phases 1-4 are sequential (2 depends on 1, 3 depends on 2, 4 depends on 3). Phase 5 is independent
of 1-4 (different statement — P&L, not balance sheet) and not yet scheduled.

## Absorbed scope: Full P&L (2026-07-07, from `260609-1107-gl-accounting-entries`)

That plan's objective (full company P&L: revenue → COGS → OpEx → net margin → EBITDA) turned out
to share the exact same prerequisite infra this plan already builds (`dim_gl_account`,
`fact_account_balance_monthly`, full-chart-of-accounts ingestion from `260702-1727`). Rather than
duplicate that infra in a separate plan, its remaining open items move here as Phase 5,
deliberately kept separate from phases 1-4 since balance sheet and P&L are different statements
with different account groupings (phase 1's asset/liability/equity flags explicitly exclude
classes 5/6/7/8 as "not a balance sheet concern" — see phase-01 line 70).

**Remaining work (not yet scheduled/detailed):**
- Extend `dim_gl_account` with P&L-side flags: `is_revenue` (class 5), `is_cogs` (632x),
  `is_opex` (641x/642x — currently lumped together in `account_class`/`cashflow_line`),
  `is_other_income` (class 7), `is_other_expense` (class 8). Same pattern as phase-01's
  asset/liability flags.
- Decide whether a named `fact_gl_entries` mart is worth promoting from the
  `src_misa_account_ledger` staging model (right grain already: account, voucher_no, posting_date,
  offset_account, debit, credit) — may be YAGNI if a monthly P&L rollup query is enough.
- Net Profit / EBITDA rollup + "Net Profit" card on the Finance dashboard —
  `docs/analytics-handbook/domains/finance.md` §12/§13 still correctly say "Planned".
- Reconcile GL revenue (511%/515%/71%) vs `fact_orders.net_revenue` — cross-check MISA-recorded
  revenue against Sapo-derived revenue before trusting either as the P&L revenue line.

## Acceptance criteria

(Phase 5 / absorbed P&L scope has its own acceptance criteria, TBD when it's scheduled — not
counted below, which covers phases 1-4 / balance sheet only.)

- [ ] `dim_gl_account` classification flags cover 100% of the 67 accounts seen in `fact_account_balance_monthly`; no `NULL` classification for an account with real posting activity.
- [ ] `fact_balance_sheet_monthly` sign-corrected: liability/equity/revenue balances are positive when in their normal (credit) direction; spot-check `331` for June 2026 shows **positive** ~952M in `current_liabilities`, not negative.
- [ ] dbt test: `total_assets ≈ total_liabilities + total_equity` per period_month (tolerance TBD in phase-02 — expect small drift from unclassified/rounding accounts, not exact zero).
- [ ] Current Ratio, Quick Ratio, DSO computable for every month from 2026-01 onward; `finance.md` metrics #16-18 show real formula + `Status: Available`, not "Planned".
- [ ] Dashboard #113 shows the 3 ratios with a documented trend-start caveat (data begins 2026-01).
- [ ] No regression to `fact_cash_movement`, `fact_account_balance_monthly`, existing dashboards #113/#114 (these are read-only inputs, not modified).

## Risks

- **Sign convention bug** (see above) — the single highest-risk item; verify with the `331` spot-check before trusting any ratio output.
- **Unclassified/garbage accounts** — a handful of `dim_gl_account` rows have garbage numeric codes from `offset_account` parsing; must not resurface once joined against the (clean) `fact_account_balance_monthly.account_code` — verify join produces no unexpected NULL-classification rows silently dropped or, worse, silently included as unclassified "other".
- **DSO revenue source (corrected 2026-07-06):** DSO's `Annual_Revenue` denominator comes from **MISA GL class-5 (511x) `period_credit`**, not Sapo `fact_orders.net_revenue` — per user: Sapo's completeness advantage is scoped to COGS only, MISA is the complete-revenue source for company-wide metrics. Both AR (numerator) and revenue (denominator) are now same-ledger (MISA) — no more cross-source mixing concern. Remaining risk: MISA full-ledger revenue history only starts 2026-01, so a true 12-month trailing window isn't available until ~2027-01 — phase-03 annualizes shorter windows meanwhile (see phase-03 SQL, `months_in_window` surfaced on the card).
- **Short history** — only ~6 months of full-ledger balance data (Jan-Jun 2026 + partial Jul). Ratios will look like a flat/short trend line for a while; not a data quality issue, just expected.
- **No long-term debt observed today** — if the company takes on a bank loan or long-term liability later (34x/343 accounts), the classification in phase-01 must already route it to `is_non_current_liability` correctly (design for this now, don't hardcode "class 3 = current" without the sub-code check), even though no such account exists in current data.
