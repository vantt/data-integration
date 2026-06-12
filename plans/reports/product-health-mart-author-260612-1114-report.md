# Product Health Mart — Author Report

**Date:** 2026-06-12 | **Scope:** mart_product_health + mart_product_action_queue

## Files Created

- `transformation/models/marts/core/mart_product_health.sql`
- `transformation/models/marts/core/mart_product_action_queue.sql`

Both use `external` parquet config with `location="{{ get_rolling_location() }}"` and `tags=['mart','product','health'|'queue']`.

---

## mart_product_health — Design Summary

**Grain:** 1 row / product_key (latest-month economics × latest inventory snapshot).

**Join spine:** `mart_sku_economics_monthly` (latest month) → LEFT JOIN `mart_inventory_health` (latest snapshot, aggregated across locations) → LEFT JOIN `int_product_velocity_trend` → LEFT JOIN `int_product_discount_dependency` → LEFT JOIN `dim_products`.

**Multi-location aggregation choice:**
- `SUM` on_hand, stock_value_at_mac, dead_stock_value_at_risk (total portfolio exposure)
- `MIN` days_of_supply (most constrained location = restock urgency driver)
- `MAX` on is_oos / is_low_stock / is_dead_stock (any-location signal)

**Classification logic:**
- `abc_class`: cumulative net_revenue DESC over all-time history → A ≤80%, B ≤95%, C rest
- `health_class`: NTILE(5) on velocity_90d × NTILE(5) on realized_margin_pct, restricted to `has_margin_data=TRUE` rows; NULL for no-margin SKUs
- `lifecycle_stage`: priority cascade — NEW (<90d since first sale) → DORMANT (>90d no sale) → DECLINING/GROWING (momentum) → MATURE
- `oos_risk`: (is_oos OR is_low_stock OR days_of_supply<14) AND (vel_score≥3 OR abc_class='A')

---

## mart_product_action_queue — Design Summary

**Grain:** product_key where action applies (filtered `WHERE action_type IS NOT NULL`).

**Source:** reads `mart_product_health` only (thin model, no re-joining raw marts).

**value_at_stake** pre-computes `avg_unit_price` from latest sku_economics as a CTE — no correlated subqueries.

| action_type | Trigger condition |
|---|---|
| RESTOCK_NOW | oos_risk = TRUE |
| CLEAR_DEADSTOCK | is_dead_stock AND dead_stock_value_at_risk > 0 |
| REVIEW_MARGIN | margin_outlier OR cogs_variance_pct > 20% OR (WORKHORSE AND DECELERATING) |
| PROMOTE | health_class = 'QUESTION' |
| DELIST | health_class = 'DOG' AND is_dead_stock |

---

## Validation Numbers (standalone DB, 2026-06-12)

Inline logic (int models computed inline; latest econ month = 2026-05, latest inv snapshot = 2026-06-05):

| Metric | Count |
|---|---|
| Total SKUs in latest econ month | 20 |
| has_margin_data = true | 17 |
| has_margin_data = false | 3 |
| health_class: STAR | 3 |
| health_class: WORKHORSE | 2 |
| health_class: QUESTION | 3 |
| health_class: DOG | 3 |
| health_class: BALANCED | 6 |
| health_class: NULL (no margin) | 3 |
| abc_class A | 7 |
| abc_class B | 3 |
| abc_class C | 10 |
| oos_risk = true | 2 |
| oos_risk = false | 18 |
| lifecycle NEW | 6 |
| lifecycle GROWING | 4 |
| lifecycle MATURE | 6 |
| lifecycle DECLINING | 4 |

**Action queue breakdown (inline):**

| action_type | cnt |
|---|---|
| REVIEW_MARGIN | 3 |
| PROMOTE | 3 |
| RESTOCK_NOW | 2 |
| CLEAR_DEADSTOCK | 0 (no dead stock with value_at_risk > 0 in latest snapshot) |
| DELIST | 0 |
| No action | 12 |

Note: standalone DB has only 20 SKUs in latest month (sparse — prod pipeline will cover full ~685 SKU catalog). Numbers above reflect current export state, not prod scale.

---

## Proposed schema.yml Blocks

```yaml
- name: mart_product_health
  description: "1-row-per-product current health state. Synthesis of velocity × margin × inventory × lifecycle. Centerpiece for Product Health dashboard."
  columns:
    - name: product_key
      tests: [not_null, unique]
    - name: sku
      tests: [not_null]
    - name: abc_class
      tests:
        - accepted_values:
            values: ['A', 'B', 'C']
    - name: health_class
      tests:
        - accepted_values:
            values: ['STAR', 'WORKHORSE', 'QUESTION', 'DOG', 'BALANCED', null]
    - name: lifecycle_stage
      tests:
        - accepted_values:
            values: ['NEW', 'GROWING', 'MATURE', 'DECLINING', 'DORMANT']
    - name: velocity_momentum
      tests:
        - accepted_values:
            values: ['ACCELERATING', 'STABLE', 'DECELERATING']

- name: mart_product_action_queue
  description: "Operational action queue — 1 row per product needing merchandising action. Drives detailView Actions tab."
  columns:
    - name: product_key
      tests: [not_null, unique]
    - name: action_type
      tests:
        - not_null
        - accepted_values:
            values: ['RESTOCK_NOW', 'CLEAR_DEADSTOCK', 'REVIEW_MARGIN', 'PROMOTE', 'DELIST']
    - name: priority_rank
      tests: [not_null]
```

---

## Caveats

1. **42-SKU margin coverage**: health_class NULL for ~643/685 SKUs without MISA COGS. Velocity/inventory/lifecycle signals still populated for all. Board must surface `has_margin_data` prominently.
2. **Standalone DB sparsity**: validation ran on 20-SKU export slice. Distributions will shift at prod scale (685 SKUs, full NTILE spread).
3. **Multi-location aggregation**: MIN(days_of_supply) is conservative — a product OOS at one location but stocked elsewhere still triggers low days_of_supply. Acceptable for restock alerting; may overcount urgency.
4. **velocity_90d from int model**: inline validation used 3-month rolling avg as proxy. Actual `int_product_velocity_trend` (other agent) may differ if it uses a 90-day rolling window on `fact_sales` directly — verify on first dbt run.
5. **DORMANT lifecycle cutoff**: 90d matches `is_dead_stock` definition. SKUs in sku_economics latest month but with days_since_last_sale > 90 are edge cases (possible if snapshot_month lag).

---

**Status:** DONE
**Summary:** Both models authored and validated inline against standalone DB. mart_product_health covers 30 columns across classification, velocity, margin, inventory, and discount signals. mart_product_action_queue is a thin downstream model reading mart_product_health with pre-computed avg_unit_price to avoid correlated subqueries.
**Concerns:** Validation on 20-SKU standalone slice — NTILE buckets with n=17 (has_margin_data) will produce uneven quintiles; at prod scale (685 SKUs) distributions will be meaningful. No CLEAR_DEADSTOCK or DELIST actions triggered in current export — expected given sparse snapshot coverage.
