# Phase 4 — Dashboard Deploy

**Depends on:** phase-03 (metrics defined + doc updated)
**Blocks:** none (final phase)

## Context

Follow this repo's tool-agnostic analytics design workflow (`CLAUDE.md` § Analytics Design / Metabase Automation) — read `.skills/analytics-design/SKILL.md` before adding cards, and `.skills/metabase-automation/STRATEGY.md` before deploying. Do not hand-edit Metabase via API/UI directly (`feedback_metabase_redeploy_use_skill` project memory) — go through the blueprint + `/deploy-metabase-blueprint` flow, same as dashboards #113/#114.

## Placement decision

Add as a **new tab on existing Metabase dashboard #113 ("Finance Cashflow")** rather than a new standalone dashboard. Rationale: same audience (CFO/finance), same cadence (monthly liquidity check alongside cash movement), avoids a 1-card-tab-count dashboard sprawl. If finance later wants this separate, splitting a tab out is cheap; merging two dashboards is not.

## Cards

1. **Scorecard — Current Ratio** (latest month), with prior-month comparison arrow.
2. **Scorecard — Quick Ratio** (latest month), with prior-month comparison arrow.
3. **Scorecard — DSO (days)** (latest month), with prior-month comparison arrow.
4. **Line chart — 3 ratios over time** (Jan 2026 → present), one line per ratio, dual-axis or normalized since Current/Quick Ratio (dimensionless multiplier, e.g. ~1.5-2.5 typical) and DSO (days, larger numbers) don't share a scale well — check `.skills/analytics-design/VISUALIZATION_VOCABULARY.md` for the right combo pattern (likely two separate small-multiple line charts rather than one crowded combo, given the scale mismatch).

All 4 cards source from `fact_balance_sheet_monthly` (ratios computed in the card SQL per phase-03's formulas, not pre-computed in the mart — consistent with how CF1-CF4 cards work off `fact_cash_movement` directly).

## Steps

1. Update `docs/analytics-handbook/designs/finance_cashflow.md` — add the new tab's viz choices (scorecard×3 + line×1 or ×2) under a "Balance Sheet & Liquidity — Phase-04 extensions" heading, same pattern the budget layer used when it extended this same dashboard (`plans/archive/260702-1727-misa-cashflow-budget-planner/phase-04-budget-hybrid.md`).
2. Update `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` — add the new tab's card definitions (SQL + viz JSON + layout), marked clearly as a new section so the existing cashflow/budget cards aren't touched.
3. Deploy: `node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` (or the project's current equivalent — confirm command from `.skills/metabase-automation/SKILL.md`, this repo's deploy script has moved before).
4. Verify field filters if any date/string filter is added on this tab — needs explicit `field_id` per `feedback_metabase_field_filter_required` project memory; run `query_metadata` to confirm the right `field_id` for `fact_balance_sheet_monthly.period_month` before wiring a filter (per `reference_metabase_field_ids_post_v2_rename` — field IDs can be stale after any rename).
5. Manual visual check in browser: scorecards render, line chart shows a short (Jan-2026-onward) but sane trend, no `NULL`/`NaN` on the current month if it's a partial month (July 2026 has only 10 rows per the phase-01/02 profiling — decide whether to exclude the current in-progress month from the scorecard "latest" pick, or show it with a "partial month" caveat; recommend excluding partial current month from the headline scorecard, same logic already used elsewhere for KPI freshness).

## Acceptance criteria

- [ ] Dashboard #113 has the new tab live, no regression to existing Cashflow/Budget tabs (spot-check a couple of existing cards still render correctly after redeploy).
- [ ] Numbers match a manual query against `fact_balance_sheet_monthly` for at least one month (recon check, same discipline as the June 2026 recon done for the original cashflow dashboard).
- [ ] Blueprint + design spec docs updated so this is the source of truth for the new tab (not just clicked together in the UI).

## Files touched

- `docs/analytics-handbook/designs/finance_cashflow.md` (edit)
- `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` (edit)
- Metabase dashboard #113 (deployed via script, not hand-edited)
