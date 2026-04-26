# Phase 5 — KPI Closure

## Context Links
- Parent: [../plan.md](./plan.md)
- Depends on: Phases 1–4 fully operational.

## Overview
- **Priority:** P3
- **Status:** ✅ IMPLEMENTED (2026-04-19)
- **Effort:** ~4h
- **Summary:** End-to-end invariant check — "revenue yesterday per Sapo web" ≈ "revenue yesterday per serving DB". Single number, single card line in morning digest.

## Implementation Notes
Implemented with feature flag `KPI_CLOSURE_ENABLED=1` (disabled by default) for controlled rollout.
Also requires `RECON_LIVE_API=1` for live Sapo API calls.

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│ @schedule health_kpi_closure_schedule (04:45 ICT daily)    │
│   target = health_kpi_closure_job                          │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│ @asset kpi_revenue_daily (group: kpi_closure)              │
│   1. Sapo API: paginate orders.json, SUM($.total)          │
│   2. Serving DB: SUM(net_revenue) from fact_orders         │
│   3. Compute drift = (warehouse - source) / source         │
│   4. Write to ingestion_health (asset_key='kpi/revenue_daily')
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│ @asset_check kpi_revenue_drift_check                       │
│   - drift > 0.5% → ERROR                                   │
│   - drift > 0.1% → WARN                                    │
└────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Created
- `orchestration/assets/kpi_closure.py` — daily revenue comparison asset
- `orchestration/asset_checks/kpi_closure_checks.py` — drift threshold checks
- `ingestion/src/sapo/api_count.py::sum_revenue_orders()` — Sapo revenue fetcher

### Modified
- `orchestration/definitions.py` — registered job, schedule, checks
- `orchestration/ops/morning_digest.py` — added 💰 Revenue line to Lark card

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KPI_CLOSURE_ENABLED` | No | `0` | Set to `1` to enable KPI closure |
| `RECON_LIVE_API` | No | `0` | Set to `1` to enable live Sapo API calls |

## Todo List
- [x] Create `orchestration/assets/kpi_closure.py`
- [x] Create `orchestration/asset_checks/kpi_closure_checks.py`
- [x] Add `sum_revenue_orders()` to `ingestion/src/sapo/api_count.py`
- [x] Update `orchestration/ops/morning_digest.py` with revenue line
- [x] Register job + schedule in `orchestration/definitions.py`
- [ ] Enable in production: `KPI_CLOSURE_ENABLED=1 RECON_LIVE_API=1`
- [ ] Calibration: verify drift < 0.5% over 7+ days before removing flag

## Success Criteria
- One line in morning card: `💰 Revenue: ✅ sapo=X ₫ | warehouse=Y ₫ | drift=Z%`
- Drift > 0.5% triggers ERROR asset check within 24h
- Drift > 0.1% triggers WARN asset check

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Revenue semantics mismatch (tax, refunds, cancelled) | High | Med | Exclude cancelled/voided; same net_revenue definition |
| Rate limiting on Sapo API (many pages) | Med | Low | safety limit 200 pages; 429 returns None gracefully |
| Timezone mismatch (UTC vs ICT) | Med | Med | date_key computed in ICT; API window in UTC |
| Feature flag forgotten | Low | None | Defaults to disabled; explicit enable required |

## Next Steps
- Enable `KPI_CLOSURE_ENABLED=1` in production
- Monitor drift values for 7+ days to calibrate thresholds
- If consistently < 0.1%, consider tightening thresholds
