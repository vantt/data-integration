---
phase: 3
title: "Downstream Refresh and Serving Sync"
status: completed
priority: P2
dependencies: [2]
---

# Phase 3: Downstream Refresh and Serving Sync

## Overview

Refresh serving layer (Metabase DuckDB views) và CRM cache để phản ánh customer_type mới, sau khi Phase 2 xác nhận blast radius an toàn.

## Requirements

- Functional: Metabase-facing serving views thấy customer_type mới.
- Functional: CRM `wh_customer_base.customer_type` cập nhật cho khách reclassified.
- Non-functional: không cần rebuild CRM container (customer_type là cột đã tồn tại, không phải schema change).

## Architecture

```
dim_customers (refreshed, Phase 1+2 verified)
         │
         ├──► bootstrap_serving_views.py (Metabase stopped) — pick up new customer_type values
         │
         └──► crm/sync/reverse_etl_warehouse_to_crm.py — re-run to sync wh_customer_base.customer_type
                (existing column, no cache_schema.sql change, no container rebuild needed)
```

## Related Code Files

- No code changes — operational refresh only
- Reference: `crm/sync/reverse_etl_warehouse_to_crm.py`, `crm/sync/cache_schema.sql:136` (existing `customer_type` column)

## Implementation Steps

1. Stop Metabase.
2. Run `bootstrap_serving_views.py` to rebuild DuckDB serving views against the refreshed `dim_customers`.
3. Restart Metabase.
4. Run CRM reverse-ETL (manual trigger or wait for next scheduled run) — no schema migration needed since `customer_type` already exists in `wh_customer_base` (`cache_schema.sql:136`); this is a normal data refresh, not a schema change, so no CRM container rebuild is required (per `feedback_crm_restart_not_rebuild.md` — data-only changes don't need `--build`).
5. Spot-check in Metabase and/or CRM that a sample of reclassified customers (from Phase 2's diff) now show `customer_type = 'CROSSBORDER'` in both surfaces.

## Success Criteria

- [x] Metabase serving views reflect new `customer_type` values — `serving/olap.duckdb` queried directly: RETAIL=5902, CROSSBORDER=1527, WHOLESALE=161, PARTNER=11 (matches warehouse)
- [x] CRM `customer_type` reflects reclassified customers after reverse-ETL run — **correction**: actual column is `wh_customer_tier.customer_type` (not `wh_customer_base`, which has no such column); ran via `crm/refresh.sh` (reverse-ETL + sync_parties + sync_party_tags), verified same distribution in `cache.db`
- [x] No CRM container rebuild needed (confirmed data-only refresh) — used existing `docker exec crm /app/refresh.sh`, no rebuild
- [x] No Metabase dashboard errors post-refresh — stopped Metabase, ran `bootstrap_serving_views.py` (73 created/replaced, 17 dropped empty folders, 0 skipped), restarted Metabase, confirmed healthy

## Risk Assessment

- **Low risk**: standard operational refresh pattern already used elsewhere in this repo (documented in project memory).
- **Risk**: forgetting to stop Metabase before `bootstrap_serving_views.py` — known footgun (`feedback_duckdb_view_rebuild.md`), call out explicitly in execution.
- **Rollback**: if Phase 1's logic needs reverting, re-run this phase's refresh steps again after the code rollback — no separate rollback procedure needed for this phase itself (it's purely a refresh trigger).
