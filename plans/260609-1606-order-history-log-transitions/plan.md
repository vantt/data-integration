---
title: "Order Status Transition Pipeline from Sapo history_log"
description: "Recover approximate order status transitions from history_log payload snapshots → lifecycle metrics mart + Metabase cards"
status: pending
# (updated 2026-06-24: untouched by 260623 audit work; stg_sapo_order_history and fact_order_status_transitions not yet built)
priority: P2
effort: 11h
branch: main
tags: [dbt, sapo, history-log, order-lifecycle, metabase]
created: 2026-06-09
---

# Order Status Transition Pipeline

Recover **approximate** order status transitions from `history_log` payload snapshots.
Each log event fetches the order's full state at fetch time, so consecutive events per
order expose status changes (`finalized → cancelled`, `draft → completed`, etc.).

## Core insight & its limit
- `payload.status` per event = entity state captured when that event was processed.
- Distinct `payload_hash` per order ≈ distinct captured states ≈ transition points.
- **Approximate only**: duplicate dlt double-ingests inflate event count; payload is
  fetch-time not event-time; events SKIPPED on fetch failure leave gaps. Transition
  TIMING is bounded by `event_timestamp`, not exact.

## Data flow
```
sapo_raw/order/ingest_method=history_log/**.parquet   (4,053 rows, 893 orders)
        │  (source sapo_v2_raw.order already globs ALL ingest_methods)
        ▼
stg_sapo_order_history   ← dedup (entity_id+event_ts+payload_hash), parse status fields
        ▼
fact_order_status_transitions  ← LAG status per order → emit row per change
        ▼  +  join fact_orders (coverage)
Metabase: order lifecycle cards (avg time-to-complete / time-to-cancel / cancel timing)
```

## Phases

| # | Phase | File | Status | Effort |
|---|-------|------|--------|--------|
| 0 | Investigate raw + API log fields + coverage | [phase-00](phase-00-investigate.md) | pending | 2h |
| 1 | dbt staging `stg_sapo_order_history` | [phase-01](phase-01-staging.md) | pending | 2h |
| 2 | dbt mart `fact_order_status_transitions` | [phase-02](phase-02-mart-transitions.md) | pending | 3h |
| 3 | Coverage & backfill analysis | [phase-03](phase-03-coverage-backfill.md) | pending | 2h |
| 4 | Metabase lifecycle cards | [phase-04](phase-04-metabase.md) | pending | 2h |

## Dependencies
- P0 blocks P1 (schema confirms parse fields) and P3 (coverage method).
- P1 blocks P2. P2 blocks P4. P3 parallel with P1/P2 (read-only analysis).
- No file overlap between P1 (staging .sql) and P2 (mart .sql) — safe if sequenced.

## Key constraints
- DuckDB warehouse `/app/var/data_lake/sapo_warehouse.duckdb`, dbt target `dev`.
- **No breaking changes** to `fact_orders` / `fact_sales` — additive models only.
- New dbt node → restart `data_platform` (manifest pre-parsed, not hot-reloaded).
- After any mart column add/rename → rebuild serving views (stop Metabase first).
- 2021-2025 NOT in history_log (Sapo truncation); coverage starts Jan 2026 only.

## Unresolved questions
See end of phase-00 and phase-03.
