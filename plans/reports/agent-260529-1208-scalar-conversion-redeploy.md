# Scalar Conversion + Redeploy Report

**Date:** 2026-05-29 12:08
**Trigger:** User request — find KPI widgets mis-displayed as `table` instead of `scalar`, fix, redeploy all.

## Context

- Metabase upgraded **v0.58.11 → v0.60.2** (verified via `/api/session/properties`)
- v0.58.11 had broken `scalar.comparisons` → many 2-col KPIs became `display: table` workaround
- v0.60.2 supports `scalar.comparisons` again → reverse the workaround

## Method

5 sonnet agents scanned all 35 blueprints in 2 passes:

**Pass 1 (conservative — 1×1 only):** 0 conversions (no widget was a single-value displayed as table)

**Pass 2 (KPI 2-col single-row):** convert when outer SELECT = exactly 2 aggregated columns (current + comparison) with no GROUP BY / single-row scalar-CTE.

## Conversions: 51 widgets / 9 files

| File | Count | Comparison style |
|---|---|---|
| `marketing_monthly_analysis.md` | 10 | MoM % / pp |
| `marketing_weekly_tracker.md` | 14 | Previous Week |
| `ceo_monthly_scorecard.md` | 6 | Thang truoc |
| `logistics_operations.md` | 6 | Hôm qua |
| `finance_pl.md` | 4 | Ky truoc |
| `b2b_sales_daily.md` | 3 | Hom qua |
| `customer_support_social_commerce.md` | 3 | Hôm qua |
| `customer_operational_dashboard.md` | 2 | Thang truoc / 30 ngay truoc |
| `channel_profitability_monthly.md` | 2 | Thang truoc |
| `sales_ops_weekly_review.md` | 1 | Tuan truoc |

Conversion pattern: `display: table` → `display: scalar` + `scalar.comparisons[].type=anotherColumn`, preserving `column_settings` currency/decimals.

## Kept as table (correctly)

- 5-col multi-period KPI tables (current, prev period, same-period-LY, MoM %, YoY %) — too dense for scalar
- All GROUP BY breakdowns (per channel, branch, SKU, etc.)
- UNION ALL multi-row summaries
- Detail/listing tables

## Redeploy

- 35 blueprints deployed via `deploy_from_markdown.js` (sequential, 1 smoke test + 34 loop)
- Log: `plans/reports/redeploy-260529-1208-all-blueprints.log`
- Result: **35/35 Deployment Complete · 0 failures**
- Metabase strategy: `v0.60.2 Modern/Dashcards`

## Open

- Visual verification on dashboard UI not done — `scalar.comparisons` settings persist in API but should be eyeballed on a sample dashboard (B2B Daily Sales / Marketing Weekly Tracker) to confirm trend arrows render.
- Memory `feedback_metabase_scalar_comparisons.md` updated to reflect v0.60.2 upgrade but flagged "needs re-verification end-to-end."
