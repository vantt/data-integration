# Phase 5 — KPI Closure (DEFERRED)

## Context Links
- Parent: [../plan.md](./plan.md)
- Depends on: Phases 1–4 fully operational.

## Overview
- **Priority:** P3 — most powerful trust signal BUT only valuable once Phases 1–4 are stable and Sapo's API surface is validated.
- **Status:** deferred (explicit user decision 2026-04-15)
- **Effort:** ~4h (estimate; revisit when unblocked)
- **Summary:** End-to-end invariant check — "revenue yesterday per Sapo web" ≈ "revenue yesterday per Metabase/serving DB". Single number, single card line, highest-signal trust check possible.

## Why Deferred
- Phases 1–4 deliver 80% of trust value without depending on a Sapo revenue-count endpoint.
- Adding KPI closure before validating the cheaper Sapo count endpoint (Phase 3 research) is premature optimization.
- User's stance: loose SLAs now, tighten later. Revenue-closure is "tighten later" territory.

## Tentative Design (to re-evaluate when activated)

1. Daily 04:45 asset `kpi_closure_revenue_daily`:
   - `sapo_revenue_yesterday` from Sapo report endpoint (or sum of `total_price` via orders.json for `created_on` BETWEEN yesterday).
   - `warehouse_revenue_yesterday` from serving DB fact table (`fct_orders` or equivalent — verify).
   - Drift = (warehouse - sapo) / sapo.
2. Write to `ingestion_health` with `asset_key = 'kpi/revenue_daily'`.
3. Asset check: abs(drift) > 0.5% → ERROR, > 0.1% → WARN.
4. Add one line to the morning Lark card above the sources table:
   `💰 Yesterday revenue: sapo=1,234,567 ₫ | warehouse=1,234,500 ₫ | drift=-0.005%`

## Pre-requisites to Un-defer

- Phase 3 research confirms Sapo has a reliable way to fetch total-revenue-in-window OR orders with `total_price` that sum consistently.
- `fct_orders` (or the chosen warehouse fact) has stable, documented semantics for "yesterday revenue".
- User explicitly requests activation.

## Related Code Files (planned)
- Create: `orchestration/assets/kpi_closure.py`, check in `orchestration/asset_checks/kpi_closure_checks.py`.
- Modify: `orchestration/definitions.py`, `orchestration/ops/morning_digest.py` (add revenue line).

## Todo List
- [ ] (deferred) activate upon user signal

## Success Criteria (when activated)
- One line in morning card showing source-vs-warehouse revenue with drift %.
- Drift > 0.5% ERROR within 24h of divergence appearing.

## Risk Assessment
- Revenue semantics (tax, shipping, refunds, cancelled orders) are notoriously divergent between source & warehouse — expect a long calibration tail. Do NOT start this phase without dedicated session.

## Next Steps
- None until pre-requisites met.
