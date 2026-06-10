# Phase 1 — dbt Staging `stg_sapo_order_history`

**Priority:** P1 (blocks P2) · **Status:** pending · **Effort:** 2h · **Blocked by:** P0

## Context links
- Pattern to mirror: `transformation/models/staging/src_sapo_orders_v2.sql` (dedup + JSON extract)
- Source: `sapo_v2_raw.order` (globs all ingest_methods → filter `history_log`)
- Schema doc: `transformation/models/staging/schema.yml`

## Overview
One **event-grain** staging model: 1 row per DEDUPED history_log event.
Deduplicate dlt double-ingests, parse the status/lifecycle fields needed for transition
detection. Do NOT collapse to latest-per-order (that's what src_sapo_orders_v2 does — this
model intentionally keeps the full event timeline).

## Key insights
- Grain difference is the whole point: src_sapo_orders_v2 = 1 row/order (latest);
  stg_sapo_order_history = 1 row/(order × distinct state event).
- Dedup key = `entity_id + event_timestamp + payload_hash` (kills dlt double-ingest).
- Source already exposes `event_timestamp`, `payload_hash`, `ingest_method`, `payload`.

## Architecture / data flow
```
sapo_v2_raw.order  --[WHERE ingest_method='history_log']-->
  dedup (ROW_NUMBER over entity_id+event_ts+payload_hash, keep rn=1)
  --> parse payload.status + lifecycle timestamps + actor
  --> 1 row per distinct event state
```

## Columns to emit
- `order_id` (entity_id), `order_code`, `event_timestamp` (cast TIMESTAMPTZ — see memory),
  `event_type` (add/update), `payload_hash`,
- `order_status` (`payload.status`), `financial_status`, `fulfillment_status`,
- lifecycle ts: `created_on, issued_on, finalized_on, cancelled_on, completed_on`,
- `actor_name` (sync_metadata.actor_name), `log_description` (sync_metadata.description),
- `total_amount` (for value-weighted metrics later).

## Materialization
- `materialized='view'` (cheap; event volume tiny ~4k). Tags `['staging','orders','history']`.
- **TIMESTAMPTZ**: cast `event_timestamp` and all `*_on` via `try_cast(... AS TIMESTAMPTZ)`
  (naive TIMESTAMP drops tz → wrong date_key for 0-7h orders — see memory).

## Related code files
- Create: `transformation/models/staging/stg_sapo_order_history.sql` (<200 lines).
- Modify: `transformation/models/staging/schema.yml` (add model + column docs + tests).
- Read for context: `src_sapo_orders_v2.sql` (copy JSON-extract idioms).

## Implementation steps
1. CTE `raw`: SELECT from `source('sapo_v2_raw','order')` WHERE `ingest_method='history_log'`.
2. CTE `deduped`: ROW_NUMBER PARTITION BY `entity_id, event_timestamp, payload_hash`
   ORDER BY `_dlt_load_id DESC`; keep rn=1.
3. CTE `parsed`: json_extract_string the columns above; try_cast timestamps to TIMESTAMPTZ.
4. Final SELECT ordered conceptually by order_id, event_timestamp.
5. schema.yml: not_null(order_id, event_timestamp); accepted_values(order_status) from P0 domain.

## Todo
- [ ] Write `stg_sapo_order_history.sql`
- [ ] Add schema.yml entry + tests
- [ ] `dbt run -s stg_sapo_order_history` (target dev) — 0 errors
- [ ] `dbt test -s stg_sapo_order_history` — pass
- [ ] Restart `data_platform` if running via Dagster (manifest reload)

## Success criteria
- [ ] Row count < raw count (dedup removed ≥ the P0 dup rate).
- [ ] `order_status` non-null for ≥99% rows; values ⊆ P0 domain.
- [ ] Distinct orders matches P0 (893±, no order dropped by dedup).

## Risk assessment
| Risk | L×I | Mitigation |
|------|-----|------------|
| dedup drops a real distinct state (same ts diff hash) | L×H | key includes payload_hash → distinct states preserved |
| timestamp parse NULLs | L×M | try_cast + not_null test catches |

## Next steps
P2 consumes this model via `ref('stg_sapo_order_history')`.
