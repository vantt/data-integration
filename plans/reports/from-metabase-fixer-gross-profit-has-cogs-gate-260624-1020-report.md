# Metabase Fixer: gross_profit has_cogs Gate — 260624-1020

**Date:** 2026-06-24  
**Source audit:** `plans/reports/from-metabase-auditor-gross-profit-null-impact-260624-0840-report.md`  
**Scope:** 20 AT-RISK fact_order_economics cards (int_misa cards SKIPPED per instructions)

---

## Phase 1 — Blueprint Coverage Map

All 20 at-risk cards are blueprint-managed. Zero cards outside blueprints.

| Card ID | Name | Blueprint File |
|---|---|---|
| 1706 | Gross Margin % | ceo_weekly_pulse.md |
| 1589 | Monthly Gross Margin % | ceo_monthly_scorecard.md |
| 2111 | Gross Margin % Trend (12M) | sales_monthly_review.md |
| 2110 | Gross Margin % vs Last Month | sales_monthly_review.md |
| 2112 | Channel Profit Contribution (Top 10) | sales_monthly_review.md |
| 2394 | Core vs Marketplace Summary | channel_profitability_monthly.md |
| 2395 | Per-Channel Profitability Table | channel_profitability_monthly.md |
| 2388 | Core vs Marketplace — Revenue & Margin Summary | channel_p_l_deep_dive.md |
| 1505 | Channel Scorecard Table | channel_p_l_deep_dive.md |
| 1511 | Loss Leader Detail Table | channel_p_l_deep_dive.md |
| 1135 | Cost Structure by Channel | order_profitability_all.md |
| 1138 | Order P&L Table | order_profitability_all.md |
| 1137 | Profit by Date | order_profitability_all.md |
| 1673 | Monthly Margin by Channel | sales_ops_monthly_summary.md |
| 1671 | Weekly Margin by Channel | sales_ops_weekly_review.md |
| 1592 | Weekly Channel Margin & Delta | marketing_weekly_tracker.md |
| 1638 | Profitable ROAS by Channel | marketing_roi.md |
| 1639 | Channel ROI Quadrant (Optional) | marketing_roi.md |
| 1640 | ROAS + Margin by Channel | marketing_monthly_analysis.md |
| 1520 | Shopee Orders Missing Fee Data | finance_accounting_recon.md |

---

## Phase 2 — Fix Applied Per Card

### Already Gated (no blueprint change needed)

These 12 cards had `has_cogs` in the blueprint SQL before this fix:

| Card ID | Name | Gate condition in blueprint |
|---|---|---|
| 1706 | Gross Margin % | `AND e.has_cogs` |
| 2110 | Gross Margin % vs Last Month | `AND e.has_cogs` |
| 2111 | Gross Margin % Trend (12M) | `AND e.has_cogs` |
| 2112 | Channel Profit Contribution (Top 10) | `AND e.has_cogs` |
| 2394 | Core vs Marketplace Summary | `WHERE foe.has_cogs` |
| 2395 | Per-Channel Profitability Table | `WHERE foe.has_cogs` |
| 2388 | Core vs Marketplace — Revenue & Margin Summary | `WHERE e.has_cogs` |
| 1505 | Channel Scorecard Table | `e.has_cogs` |
| 1511 | Loss Leader Detail Table | `e.has_cogs` |
| 1135 | Cost Structure by Channel | `e.has_cogs` |
| 1137 | Profit by Date | `e.has_cogs` |
| 1138 | Order P&L Table | `e.has_cogs` |

### Fixed in This Run

| Card ID | Name | Blueprint | Fix Applied |
|---|---|---|---|
| 1589 | Monthly Gross Margin % | ceo_monthly_scorecard.md | Added `AND has_cogs` to all 3 CTEs (this_month, prev_month, prev_year) |
| 1673 | Monthly Margin by Channel | sales_ops_monthly_summary.md | Added `AND e.has_cogs` to this_period + prev_period CTEs; removed COALESCE masking from SUM(gross_profit) |
| 1671 | Weekly Margin by Channel | sales_ops_weekly_review.md | Added `AND e.has_cogs` to this_week + last_week CTEs; removed COALESCE masking from SUM(gross_profit) |
| 1592 | Weekly Channel Margin & Delta | marketing_weekly_tracker.md | Added `AND oe.has_cogs`; also fixed pre-existing bug: `oe.ordered_at` → `oe.date_key` integer filter (fact_order_economics has no ordered_at column) |
| 1638 | Profitable ROAS by Channel | marketing_roi.md | Added `AND e.has_cogs` to current_econ + prior_econ CTEs |
| 1639 | Channel ROI Quadrant (Optional) | marketing_roi.md | Added `AND e.has_cogs` to channel_econ CTE |
| 1640 | ROAS + Margin by Channel | marketing_monthly_analysis.md | Added `AND o.has_cogs` to perf CTE; fixed pre-existing bug: `o.ordered_at` → `o.date_key` integer filter in perf + prev_perf CTEs; also fixed Channel Profit Contribution vs Spend card (profit_cur, profit_prev CTEs, same ordered_at bug) |
| 1520 | Shopee Orders Missing Fee Data | finance_accounting_recon.md | Added `AND fact_order_economics.has_cogs` — prevents NULL gross_profit in diagnostic column; note: NULLs for no-COGS shopee orders would be misleading in this recon context |

---

## Deploy Results

| Blueprint | Deploy | Cards Updated |
|---|---|---|
| ceo_monthly_scorecard.md | ✅ Success | 43 synced |
| sales_ops_monthly_summary.md | ✅ Success | 56 synced |
| sales_ops_weekly_review.md | ✅ Success | 46 synced |
| marketing_weekly_tracker.md | ✅ Success (2 deploys: has_cogs + ordered_at fix) | 49 synced |
| marketing_roi.md | ✅ Success | 15 synced |
| marketing_monthly_analysis.md | ✅ Success (2 deploys: has_cogs + ordered_at fix) | 64 synced |
| finance_accounting_recon.md | ✅ Success | 26 synced |

---

## Verification Results

API `GET /api/card/:id` + `POST /api/card/:id/query` run for all 8 fixed cards:

| Card ID | has_cogs in SQL | Query Result |
|---|---|---|
| 1589 | ✅ True | OK — Gross Margin %: 41.4, rows: 1 |
| 1673 | ✅ True | OK — rows: 32 |
| 1671 | ✅ True | OK — rows: 30 |
| 1592 | ✅ True | OK — rows: 4, margin values non-null |
| 1638 | ✅ True | OK — rows: 4 |
| 1639 | ✅ True | OK — rows: 2 |
| 1640 | ✅ True | OK — rows: 6 |
| 1520 | ✅ True | OK — rows: 200 |

---

## Blueprint Files Edited (for commit)

1. `docs/analytics-handbook/blueprints/metabase/ceo_monthly_scorecard.md`
2. `docs/analytics-handbook/blueprints/metabase/sales_ops_monthly_summary.md`
3. `docs/analytics-handbook/blueprints/metabase/sales_ops_weekly_review.md`
4. `docs/analytics-handbook/blueprints/metabase/marketing_weekly_tracker.md`
5. `docs/analytics-handbook/blueprints/metabase/marketing_roi.md`
6. `docs/analytics-handbook/blueprints/metabase/marketing_monthly_analysis.md`
7. `docs/analytics-handbook/blueprints/metabase/finance_accounting_recon.md`

---

## Cards NOT Fixed via Blueprint

None. All 20 at-risk cards were blueprint-managed and have been addressed.

---

## Unresolved Questions

1. **Fraction of orders where has_cogs = FALSE:** Not measured — determines how much the aggregates shifted post-fix. Recommend running: `SELECT COUNT(*), COUNT(*) FILTER (WHERE has_cogs) FROM main_marts.fact_order_economics` to size the drift.
2. **Card 1520 (Shopee Missing Fee Data):** Added `has_cogs` gate. Auditor noted NULLs may be informative for diagnostic purposes. With `gross_profit` now NULL for no-COGS rows, showing them would display NULL in "Gross Profit (VND)" column — agreed the gate is cleaner for this recon surface. Confirm if this is acceptable.
3. **pre-existing `ordered_at` bugs fixed as collateral:** Cards 1592, 1640 (and related "Channel Profit Contribution vs Spend" in same blueprint) used `o.ordered_at`/`oe.ordered_at` on `fact_order_economics` which has no such column. These were pre-existing failures, now fixed to use `date_key` integer filter. These cards were already broken before this change — confirm the date_key substitution matches expected window semantics.
4. **int_misa cards (11 cards):** Skipped per instructions. H010 gross_profit correction is a separate model-level issue.
