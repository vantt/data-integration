# Plan: Targets and Forecasting Pace

> Created: 2026-06-09
> Status: ✅ Partially done
> Origin: `analytics_improvement_opportunities.md` § Targets and Forecasting Inputs

## Objective

Make pace and target dashboards prescriptive — forecasted month-end, required daily run-rate, gap bridge, early warning.

## Current state

**✅ Done:**
- `fact_targets`: 48 rows, `metric_code = 'gmv'`, `cycle_type = 'monthly'`, 300M/month
- Live in CEO Weekly Pulse MTD GMV vs Target card (progress viz, static goal = 300M × 2 = 600M/month)

**Not yet built:**
- Pace index (actual-to-date / expected-to-date based on day-of-month)
- Forecasted month-end revenue
- Required daily run-rate to hit target
- Gap bridge: decompose variance into volume, AOV, channel mix, discount, return/cancel
- Target granularity beyond GMV/monthly (channel, branch, product category, team)
- Promotion calendar / seasonality curves

## Data in `fact_targets`

| field | current state |
|---|---|
| metric_code | `gmv` only |
| cycle_type | `monthly` only |
| target_val | 300M / month |
| branch_key | NULL (no branch-level target) |
| channel_key | NULL (no channel-level target) |
| staff_key | NULL (no staff-level target) |

## Implementation steps

- [ ] Add pace index to CEO Weekly Pulse: `(actual_mtd / target) / (day_of_month / days_in_month)`
- [ ] Add forecasted month-end card: `actual_mtd / (day_of_month / days_in_month)`
- [ ] Add required daily run-rate: `(target - actual_mtd) / remaining_days`
- [ ] Add Target Gap Bridge to CEO Monthly Scorecard:
  - Target Revenue
  - Actual Revenue
  - Order Volume Impact
  - AOV Impact
  - Discount Impact
  - Return/Cancel Impact
  - Channel Mix Impact
- [ ] Expand `fact_targets` grain: add channel, branch targets when finance provides them
- [ ] Add "Top 5 Decisions This Week" table to CEO Weekly Pulse (signal / why / owner / action / link)

## Dependency

Gap bridge requires no new data — uses existing `fact_orders` + `fact_targets`.
Channel/branch targets require manual input from finance team into target seed/gsheet.
