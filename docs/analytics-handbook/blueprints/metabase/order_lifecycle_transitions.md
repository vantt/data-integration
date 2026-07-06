---
primary_scope: none
scope_indicator: "[Cross]"
layer: L1
uses_concepts: []
---

# 📘 Blueprint: Order Lifecycle Transitions [Cross]

> **Database:** Sapo
> **Role:** Operations
> **Archetype:** Diagnostic (approximate, Jan 2026+ only)

## Semantic Contract

Not tied to an existing semantic concept (`primary_scope: none`). Source mart
`fact_order_transitions` is derived from Sapo `history_log` payload snapshots —
**approximate**, not a true event log: transition timing is bounded by the fetch
timestamp of the snapshot that first captured the new state, not the true change
instant. See `plans/archive/260609-1606-order-history-log-transitions/plan.md` for the
full approximation contract and `plans/reports/p3-coverage-backfill-analysis-260706-1739-order-history-log-transitions-report.md`
for coverage validation (99.9% of Jan-2026+ orders).

## 📂 Collection: Operations > Order Lifecycle

### Dashboard: Order Lifecycle Transitions [Cross]

**Description**: Time-to-complete / time-to-cancel timing derived from Sapo history_log
snapshot diffing. Approximate — see coverage/caveat card. Data starts Jan 2026 (history_log
truncation before that).

#### ❓ Question: Coverage & Caveat

```sql
WITH fo AS (
    SELECT order_id
    FROM main_marts.fact_orders
    WHERE ordered_at >= '2026-01-01'
),
hl AS (
    SELECT DISTINCT order_id
    FROM main_marts.fact_order_transitions
)
SELECT
    '📊 History-log coverage: ' ||
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN hl.order_id IS NOT NULL THEN fo.order_id END) / COUNT(DISTINCT fo.order_id), 1) ||
    '% of orders (Jan 2026+). Timing below is APPROXIMATE — derived from snapshot diffing, not an exact event log.'
    AS "Coverage & Caveat"
FROM fo
LEFT JOIN hl ON fo.order_id = hl.order_id
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: Avg Time to Complete (Trend by Month)

Mean days from first observed snapshot to the `completed` transition, by month completed.

```sql
WITH first_seen AS (
    SELECT order_id, MIN(event_timestamp) AS first_ts
    FROM main_marts.fact_order_transitions
    GROUP BY order_id
),
completed AS (
    SELECT order_id, event_timestamp AS completed_ts
    FROM main_marts.fact_order_transitions
    WHERE transition_type = 'completed'
)
SELECT
    date_trunc('month', completed.completed_ts)::DATE AS completed_month,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed.completed_ts - first_seen.first_ts)) / 86400.0), 2) AS avg_days_to_complete
FROM completed
JOIN first_seen USING (order_id)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["completed_month"],
    "graph.metrics": ["avg_days_to_complete"]
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Avg Time to Cancel

Mean hours from first observed snapshot to the `cancelled` transition (all-time, Jan 2026+).

```sql
WITH first_seen AS (
    SELECT order_id, MIN(event_timestamp) AS first_ts
    FROM main_marts.fact_order_transitions
    GROUP BY order_id
),
cancelled AS (
    SELECT order_id, event_timestamp AS cancelled_ts
    FROM main_marts.fact_order_transitions
    WHERE transition_type = 'cancelled'
)
SELECT
    ROUND(AVG(EXTRACT(EPOCH FROM (cancelled.cancelled_ts - first_seen.first_ts)) / 3600.0), 1) AS avg_hours_to_cancel
FROM cancelled
JOIN first_seen USING (order_id)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 2, "col": 12, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Cancel Timing Distribution

Histogram of hours-to-cancel per cancelled order — how fast do cancels happen after first observation?

```sql
WITH first_seen AS (
    SELECT order_id, MIN(event_timestamp) AS first_ts
    FROM main_marts.fact_order_transitions
    GROUP BY order_id
),
cancelled AS (
    SELECT order_id, event_timestamp AS cancelled_ts
    FROM main_marts.fact_order_transitions
    WHERE transition_type = 'cancelled'
)
SELECT
    ROUND(EXTRACT(EPOCH FROM (cancelled.cancelled_ts - first_seen.first_ts)) / 3600.0, 1) AS hours_to_cancel
FROM cancelled
JOIN first_seen USING (order_id)
```

```json metabase-viz
{ "display": "bar", "visualization_settings": { "graph.x_axis.scale": "histogram" } }
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```
