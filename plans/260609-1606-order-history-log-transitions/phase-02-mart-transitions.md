# Phase 2 — dbt Mart `fact_order_status_transitions`

**Priority:** P1 (blocks P4) · **Status:** pending · **Effort:** 3h · **Blocked by:** P1

## Context links
- Input: `stg_sapo_order_history` (phase-01)
- Mart materialization pattern: `fact_orders.sql` config (parquet + get_rolling_location)
- Status dim: `dim_order_status.sql`

## Overview
Transition-grain fact: **1 row per detected status CHANGE per order**.
LAG `order_status` over events ordered by `event_timestamp` per order; emit a row only
when `order_status != prev_status`. Compute dwell time in prior state.

## Key insight / approximation contract
- A "transition" = first event where captured status differs from prior captured status.
- `from_status` may be NULL on first observed event (= initial observed state, not a real transition — flag it `is_initial_observation=true`).
- `transition_at = event_timestamp` of the event carrying the NEW status. This is an
  UPPER BOUND on true transition time (status changed at or before this fetch). Document this.
- `dwell_seconds` = transition_at − prev transition_at (time spent in from_status, approximate).

## Architecture / data flow
```
stg_sapo_order_history (event grain)
  --> window: LAG(order_status) OVER (PARTITION BY order_id ORDER BY event_timestamp)
  --> filter status != prev_status (OR first row)
  --> compute dwell_seconds, transition sequence number
  --> 1 row per transition
```

## Columns
- `transition_key` (surrogate: order_id + transition_seq), `order_id`, `order_code`,
- `transition_seq` (1..N), `from_status`, `to_status`,
- `from_at` (prev transition_at, NULL if initial), `to_at` (transition_at TIMESTAMPTZ),
- `dwell_seconds` (NULL if initial), `is_initial_observation` (bool),
- `is_terminal` (to_status ∈ {completed, cancelled}), `actor_name`, `total_amount`.

## Materialization
- `materialized='table'`, parquet export, `location=get_rolling_location()` (mirror fact_orders).
- Tags `['mart','fact']`. Rolling GC runs per materialization (see recent commit 76ee4e8).

## Related code files
- Create: `transformation/models/marts/sales/fact_order_status_transitions.sql` (<200 lines).
- Modify: `transformation/models/marts/schema.yml` (model + tests + column docs).
- Read for context: `fact_orders.sql` (config block), `stg_sapo_order_history.sql`.

## Implementation steps
1. CTE `events`: SELECT from `ref('stg_sapo_order_history')`, only rows with non-null status.
2. CTE `with_lag`: add `prev_status = LAG(order_status)` and `prev_at = LAG(event_timestamp)`
   over (PARTITION BY order_id ORDER BY event_timestamp, payload_hash).
3. CTE `changes`: WHERE `prev_status IS NULL OR order_status != prev_status`.
4. Compute `transition_seq = ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_timestamp)`,
   `dwell_seconds = date_diff('second', prev_at, event_timestamp)`,
   `is_initial_observation = (prev_status IS NULL)`.
5. surrogate key via dbt_utils.generate_surrogate_key([order_id, transition_seq]).
6. schema.yml: unique(transition_key), not_null(order_id,to_status,to_at),
   relationships to_status → dim_order_status (accepted_values lowercase ↔ dim uppercase: normalize).

## Todo
- [ ] Write `fact_order_status_transitions.sql`
- [ ] Add schema.yml + tests
- [ ] `dbt run -s fact_order_status_transitions` (dev) — 0 errors
- [ ] `dbt test -s fact_order_status_transitions` — pass
- [ ] Rebuild serving views (stop Metabase first) so Metabase sees new mart
- [ ] Restart data_platform (manifest reload)

## Success criteria
- [ ] Orders with ≥2 distinct states produce ≥1 transition row.
- [ ] `dwell_seconds >= 0` for all non-initial rows.
- [ ] terminal-state orders (completed/cancelled in latest) have a matching terminal transition.
- [ ] Cross-check: count of orders reaching `cancelled` ≈ 198, `completed` ≈ 372 (P0 baseline).

## Risk assessment
| Risk | L×I | Mitigation |
|------|-----|------------|
| status flapping (fetch noise) inflates transitions | M×M | dedup in P1 + payload_hash tiebreak; flag rapid (<60s) transitions |
| dim_order_status case mismatch (UPPER vs lower) | H×L | normalize UPPER in relationship test or add lower aliases |
| missing intermediate states (gaps) | M×M | document approximation; is_initial flag isolates |

## Backwards compatibility
Purely additive new mart. Zero edits to fact_orders/fact_sales lineage. Rollback = drop model
+ remove serving view; no downstream consumer until P4.

## Next steps
P4 builds Metabase cards on this mart.
