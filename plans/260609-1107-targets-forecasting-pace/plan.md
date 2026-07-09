# Plan: Targets and Forecasting Pace

> Created: 2026-06-09
> Status: ✅ Partially done — In progress
> Origin: `analytics_improvement_opportunities.md` § Targets and Forecasting Inputs
> (updated 2026-07-08: added Forecasted Month-End GMV + Required Daily Run-Rate cards to CEO Weekly Pulse; gap-bridge/grain-expansion still not built)

## Objective

Make pace and target dashboards prescriptive — forecasted month-end, required daily run-rate, gap bridge, early warning.

## Current state

**✅ Done:**
- `fact_targets`: 48 rows, `metric_code = 'gmv'`, `cycle_type = 'monthly'`, 300M/month — unchanged since 2026-06-09
- Live in CEO Weekly Pulse MTD GMV vs Target card (progress viz, static goal = 300M × 2 = 600M/month)
- **Pace Index** — gauge card in `ceo_weekly_pulse.md` (row 7, col 12): `mtd_gmv / (target_gmv × day_of_month / days_in_month)`, segments Behind (<0.8) / On Track (0.8–1.0) / Ahead (>1.0). Formula matches plan spec exactly.
- **Forecasted Month-End GMV** (NEW 2026-07-08) — progress card in `ceo_weekly_pulse.md` (row 28, col 0): `mtd_gmv / (day_of_month / days_in_month)`, same static-goal caveat as MTD GMV vs Target (600,000,000)
- **Required Daily Run-Rate** (NEW 2026-07-08) — scalar card in `ceo_weekly_pulse.md` (row 28, col 12): `GREATEST(target_gmv - mtd_gmv, 0) / remaining_days`
- **`dim_channel_targets`** (separate model) — channel-level budget by month for NET_REVENUE/NET_MARGIN_PCT/ORDER_COUNT, feeds `finance_channel_pl.md` + `channel_p_l_deep_dive.md` blueprints. Seeded from `seed_channel_targets.csv` — **all rows explicitly labeled "Placeholder — update with real budget"**, not real finance numbers yet. This is a parallel path to `fact_targets`, not a grain expansion of it.

**Not yet built:**
- Gap bridge: decompose variance into volume, AOV, channel mix, discount, return/cancel
- `fact_targets` grain expansion — schema already supports it (`branch_key`/`staff_key`/`channel_key`/`product_key` columns exist in the model with `Unknown` fallback), but **all 48 rows still have `scope_branch/staff/channel/product = 'ALL'`** — no actual sub-GMV target has been loaded
- Promotion calendar / seasonality curves
- "Top 5 Decisions This Week" table

## Data in `fact_targets`

| field | current state (re-verified 2026-07-08) |
|---|---|
| metric_code | `gmv` only |
| cycle_type | `monthly` only |
| target_val | 300M / month |
| row count | 48 (unchanged) |
| branch_key / staff_key / channel_key / product_key | columns exist (added since 2026-06-09) but all rows resolve to `Unknown`/`ALL` — no data loaded |

## Implementation steps

- [x] Add pace index to CEO Weekly Pulse: `(actual_mtd / target) / (day_of_month / days_in_month)` — shipped, gauge card in `ceo_weekly_pulse.md`
- [x] Add forecasted month-end card: `actual_mtd / (day_of_month / days_in_month)` — shipped 2026-07-08, progress card in `ceo_weekly_pulse.md`
- [x] Add required daily run-rate: `(target - actual_mtd) / remaining_days` — shipped 2026-07-08, scalar card in `ceo_weekly_pulse.md`
- [ ] Add Target Gap Bridge to CEO Monthly Scorecard:
  - Target Revenue
  - Actual Revenue
  - Order Volume Impact
  - AOV Impact
  - Discount Impact
  - Return/Cancel Impact
  - Channel Mix Impact
- [ ] Expand `fact_targets` grain: add channel, branch targets when finance provides them — columns exist, no data populated; `dim_channel_targets` covers channel budget separately but with placeholder values only
- [ ] Add "Top 5 Decisions This Week" table to CEO Weekly Pulse (signal / why / owner / action / link)

## Dependency

Gap bridge requires no new data — uses existing `fact_orders` + `fact_targets`.
Channel/branch targets require manual input from finance team into target seed/gsheet.
