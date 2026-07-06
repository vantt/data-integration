# Plan: CRM Runtime Metrics → Data Warehouse Pre-computation

**Status:** DONE  
**Branch:** main  
**Date:** 2026-06-30  
**Phases:** P0 · P1 · P2

---

## Context

Recent CRM clean-code phase (commit `0ab8243`) extracted computation from templates into domain entities (`order.py`, `cache_insight.py`, `party.py`, `task.py`) and the `worklist_ranking.py` module. This is correct domain encapsulation — but the audit reveals a harder problem: **several of these computations are core business metrics that should not be computed at request time at all.** They belong pre-computed in the warehouse.

Two classes of problem:

1. **Live DuckDB fan-out on every C360 page load** — `CustomerDimMetricsRepository` executes a `fact_orders × fact_order_economics` JOIN per customer request instead of reading from `dim_customers`. The results are metrics that `int_customer_economics` could trivially expose.

2. **Per-order Python aggregations** — `OrderDetail.cogs_reconciliation_totals` and `CogsItem.variance*` aggregate line-level data in Python. These are stable facts once an order is completed; they belong in the warehouse where they can be queried, monitored, and made available to Metabase.

---

## Findings: What to Move vs What to Keep

### ✅ MOVE to warehouse (core metrics / values)

| # | Computation | Current location | Where it lives now | Where it should live |
|---|------------|-----------------|-------------------|---------------------|
| 1 | `total_cogs` = SUM(cogs_amount) | `customer_dim_metrics_sql.py` (live) | Absent from dim | `int_customer_economics` → `dim_customers` |
| 2 | `avg_gross_margin_pct` = AVG(gross_margin_pct) | `customer_dim_metrics_sql.py` (live) | Absent (dim has contribution-margin variant) | `int_customer_economics` → `dim_customers` |
| 3 | `total_return_amount` = SUM(return_amount) | `customer_dim_metrics_sql.py` (live) | Absent from dim | `int_customer_economics` → `dim_customers` |
| 4 | `return_count` = SUM(return_count) | `customer_dim_metrics_sql.py` (live) | Absent from dim | `int_customer_economics` → `dim_customers` |
| 5 | `cogs_order_count` INTEGER | `customer_dim_metrics_sql.py` (live) | Only ratio (`margin_cogs_coverage_pct`) | `int_customer_economics` → `dim_customers` |
| 6 | `cogs_coverage_pct` INT% | `CustomerDimMetrics.cogs_coverage_pct` property | Ratio in dim, count absent | Derived from (5), add to `dim_customers` |
| 7 | `order_discount_rate` = discount_amount / gross_revenue | `OrderFinancial.discount_rate` property | Absent from economics mart | `fact_order_economics` |
| 8 | `cogs_variance` = sapo − misa (per SKU) | `CogsItem.variance` property | Absent | `int_order_cogs_reconciled` |
| 9 | `cogs_variance_pct` = variance / misa × 100 | `CogsItem.variance_pct` property | Absent | `int_order_cogs_reconciled` |
| 10 | `is_high_cogs_variance` BOOL | `CogsItem.is_high_variance` property | Absent | `int_order_cogs_reconciled` |
| 11 | Order-level COGS recon totals | `OrderDetail.cogs_reconciliation_totals` | Absent | New mart `mart_order_cogs_summary` |
| 12 | `is_high_cancel_risk` BOOL (threshold 25%) | `CustomerInsight.is_high_cancel_risk` property | Absent from dim | `dim_customers` + update Python constant to 0.25 |

### 🔒 KEEP in domain (not warehouse candidates)

| Computation | Why keep in domain |
|------------|-------------------|
| `composition_segments()` — normalized display bar pct | CRM UI concern; thresholds could change per rep view |
| `cogs_source_label` — UI string | Pure presentation |
| `StatusSnapshot.abbreviation` / `tooltip_text` | Template display only |
| `CacheInsight.sorted_actions` / `has_active_actions` / `unresolved_count` | Depends on `crm_action_state` (CRM-side dismiss/snooze) |
| `CacheInsight.best_next_purchase_display` | Cross-entity aggregation gated by CRM action state |
| `worklist_ranking.urgency_score` / `assign_band` | Cross-domain (CRM tasks + warehouse actions), needs runtime date comparison |
| `Task.priority_label` | UI label |
| `Task.is_overdue_at` | Runtime datetime comparison against wall clock |
| `partition_identities_by_channel` | CRM identity grouping, no warehouse involvement |

---

## Decision Notes

### avg_gross_margin_pct vs avg_order_contribution_margin_pct — both needed

Both are customer-level averages. Difference: `channel_net_profit = gross_profit − Shopee_fees`. For non-Shopee customers the two are identical.

| | `avg_gross_margin_pct` | `avg_order_contribution_margin_pct` |
|--|---|---|
| Formula | AVG(gross_profit / net_revenue) | AVG(channel_net_profit / net_revenue) |
| Shopee fees | not deducted | ✅ deducted |
| Customer-level question | "Biên gộp sau COGS — trước chi phí kênh?" | "Thực tế khách mang về sau mọi chi phí trực tiếp?" |
| CRM surface | C360 Profitability → "Avg margin" (pricing/COGS signal) | `lifetime_contribution_margin` → LTV KPI |

`dim_customers` has the contribution variant. `avg_gross_margin_pct` (gross basis) is **missing** → Phase 1 adds it to `int_customer_economics` by pulling `foe.gross_margin_pct` into the CTE.

### is_high_cancel_risk — threshold 25%, add to warehouse

Threshold decision: **25%** (hơn 1/4 đơn bị hủy = pattern ổn định, không ngẫu nhiên).
- 10% (cũ) quá thấp: COD customers từ chối nhận bình thường có thể chạm ngưỡng → false positive
- 50% quá cao: chỉ bắt extreme outlier, dùng cho action trigger riêng
- 25%: early warning badge, rep để ý mà không bị spam

| Location | Threshold | Purpose | Change |
|----------|-----------|---------|--------|
| Python `CANCEL_RISK_THRESHOLD` | 10% → **25%** | C360 badge display | Update constant |
| warehouse `is_high_cancel_risk` (new) | **> 25%** | Queryable in Metabase | Add to dim_customers |
| `mart_customer_action_queue.sql` | **> 50% AND order_count ≥ 3** | Action trigger | Giữ nguyên |

Two thresholds (25% badge, 50% action trigger) are intentional and distinct. Item 12 is reinstated: add `is_high_cancel_risk BOOL` to `dim_customers`.

### mart_order_cogs_summary — daily cadence

COGS data only changes on MISA/Sapo pipeline refreshes (not real-time). Daily sync in the pipeline schedule is sufficient.

---

## Phases

### Phase 0 — Prep: understand impact scope

- Confirm `int_customer_economics` column additions don't break downstream snapshots
- Confirm `fact_order_economics` schema additions don't break existing `wh_order_hdr` serving views
- Confirm `int_order_cogs_reconciled` has no downstream models that would need recompile
- Mark `VALUE_METRICS_BY_CUSTOMER_KEY` in `customer_dim_metrics_sql.py` as the deletion target

### Phase 1 — Customer profitability aggregates in dim_customers (items 1-6, 12)

**Files:** `transformation/models/marts/core/intermediate/int_customer_economics.sql`, `transformation/models/marts/core/dim_customers.sql`, `crm/src/adapters/outbound/duckdb/customer_dim_metrics_sql.py`, `crm/src/domain/entities/cache_insight.py`

**Steps:**

1. Add to `int_customer_economics.sql`:
   ```sql
   SUM(oe.gross_profit) FILTER (WHERE oe.has_cogs)            AS total_gross_profit,  -- already: lifetime_gross_profit (same)
   SUM(oe.cogs_amount) FILTER (WHERE oe.has_cogs)             AS total_cogs,
   AVG(oe.gross_margin_pct) FILTER (WHERE oe.has_cogs)        AS avg_gross_margin_pct,
   SUM(oe.return_amount)                                       AS total_return_amount,
   SUM(oe.return_count)                                       AS return_count,
   COUNT(*) FILTER (WHERE oe.has_cogs)                        AS cogs_order_count,
   -- derived
   (cancel_rate > 0.10)                                        AS is_high_cancel_risk,
   ```
   Note: `cancel_rate` comes from `int_customer_metrics` (already joined in dim_customers). `is_high_cancel_risk` stays as Python property — NOT added to warehouse (see Decision Notes).

   For `avg_gross_margin_pct`: the existing CTE in `int_customer_economics` only has `channel_net_profit`. Must also pull `foe.gross_margin_pct` from `fact_order_economics`.

2. Expose in `dim_customers.sql` SELECT and final output.

3. Rewrite `VALUE_METRICS_BY_CUSTOMER_KEY` in `customer_dim_metrics_sql.py` to:
   ```sql
   SELECT total_cogs, avg_gross_margin_pct, total_return_amount, return_count,
          cogs_order_count, frequency AS order_count, lifetime_gross_profit AS total_gross_profit,
          margin_cogs_coverage_pct, is_high_cancel_risk,
          lifecycle_stage, product_affinity, payment_behavior, geo_region, customer_type, first_order_date
   FROM main_marts.dim_customers
   WHERE customer_id = CAST(? AS VARCHAR)
   LIMIT 1
   ```
   → collapses 2 queries into 1, eliminates the `fact_orders × fact_order_economics` join.

4. Update `CustomerDimMetrics` entity: remove `cogs_coverage_pct` property (now a raw column), remove `has_partial_cogs_coverage` property (recompute from raw columns or keep as property over warehouse integers).

5. Update `CustomerInsight.is_high_cancel_risk` property: keep as Python property for backward compat BUT add note it's now redundant with warehouse column (can be removed in follow-up clean).

**Tests / validation:**
- Run dbt for `int_customer_economics` and `dim_customers`, check row count unchanged
- Compare `cogs_order_count / order_count` with old `margin_cogs_coverage_pct` — must match within float precision
- C360 page load: verify `dim_metrics` panel shows same values

---

### Phase 2 — Order-level discount rate (item 7)

**Files:** `transformation/models/marts/sales/fact_order_economics.sql`, `crm/src/domain/entities/order.py`

**Steps:**

1. Add to `fact_order_economics.sql` final SELECT:
   ```sql
   CASE
       WHEN o.gross_revenue > 0
       THEN o.discount_amount::DOUBLE / o.gross_revenue
       ELSE NULL
   END AS order_discount_rate,
   ```
   (`gross_revenue` is already joined from `fact_orders`)

2. Expose via `wh_order_hdr` serving view if the CRM reads the order header from cache.db.

3. Update `OrderFinancial.discount_rate` property → retire the Python division, read pre-computed column instead (requires order mapper update).

**Note:** `wh_order_hdr` is baked into `cache.db`; the serving view SQL will need the column added to its SELECT.

---

### Phase 3 — COGS reconciliation in warehouse (items 8-11)

**Files:** `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql`, new `transformation/models/marts/sales/mart_order_cogs_summary.sql`, `crm/src/domain/entities/order.py`

**Steps:**

1. Add to `int_order_cogs_reconciled.sql` final SELECT:
   ```sql
   cogs_goods_sapo - cogs_goods_misa                           AS cogs_variance,
   CASE WHEN cogs_goods_misa != 0 AND cogs_goods_misa IS NOT NULL
        THEN (cogs_goods_sapo - cogs_goods_misa)::DOUBLE / cogs_goods_misa * 100
        ELSE NULL END                                           AS cogs_variance_pct,
   ABS((cogs_goods_sapo - cogs_goods_misa)::DOUBLE
       / NULLIF(cogs_goods_misa, 0) * 100) > 10.0              AS is_high_cogs_variance,
   ```

2. Create `mart_order_cogs_summary.sql` (grain: order_code):
   ```sql
   SELECT
       order_code,
       SUM(cogs_goods_sapo) AS sapo_total,
       SUM(cogs_goods_misa) AS misa_total,
       SUM(cogs_goods_sapo) - SUM(cogs_goods_misa) AS variance,
       CASE WHEN SUM(cogs_goods_misa) != 0
            THEN (SUM(cogs_goods_sapo) - SUM(cogs_goods_misa))::DOUBLE
                 / SUM(cogs_goods_misa) * 100
            ELSE NULL END AS variance_pct,
       ABS(...) > 10.0 AS is_high_variance
   FROM int_order_cogs_reconciled
   GROUP BY order_code
   ```

3. Sync `mart_order_cogs_summary` into cache.db via reverse-ETL (similar to `wh_action_queue`).

4. Update `OrderDetail.cogs_reconciliation_totals` property → read from pre-synced cache table instead of aggregating `cogs_items` in Python.

5. Update `CogsItem.variance*` properties → retire, read columns from DB row.

**Acceptance criteria:**
- `mart_order_cogs_summary` row count = distinct order_codes in `int_order_cogs_reconciled`
- Order detail COGS tab: reconciliation footer shows same totals as before
- dbt test: `variance = sapo_total - misa_total` for all rows

---

## Affected Files Summary

| File | Change |
|------|--------|
| `transformation/models/marts/core/intermediate/int_customer_economics.sql` | Add 6 columns: total_cogs, avg_gross_margin_pct, total_return_amount, return_count, cogs_order_count, is_high_cancel_risk |
| `transformation/models/marts/core/dim_customers.sql` | Expose new columns from int_customer_economics |
| `transformation/models/marts/sales/fact_order_economics.sql` | Add order_discount_rate column |
| `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql` | Add cogs_variance, cogs_variance_pct, is_high_cogs_variance |
| `transformation/models/marts/sales/mart_order_cogs_summary.sql` | **NEW** — order-grain COGS reconciliation mart |
| `crm/src/adapters/outbound/duckdb/customer_dim_metrics_sql.py` | Rewrite VALUE_METRICS query; eliminate live fact_orders join |
| `crm/src/adapters/outbound/duckdb/customer_dim_metrics_repository.py` | Map new column names from dim_customers |
| `crm/src/domain/entities/cache_insight.py` | `cogs_coverage_pct` property: update to use raw int count; retire `is_high_cancel_risk` as warehouse-sourced |
| `crm/src/domain/entities/order.py` | `CogsItem.variance*`: read from columns; `OrderDetail.cogs_reconciliation_totals`: read from pre-computed table |
| `crm/sync/cache_schema.sql` | Add `wh_order_cogs_summary` table for mart sync |

---

## Risks

- `dim_customers` is consumed by Metabase and serving views — adding columns is additive (safe), but dbt full-refresh needed if the model is incremental.
- `int_order_cogs_reconciled` is read by `fact_order_economics` — adding columns is additive.
- `mart_order_cogs_summary` sync requires a new reverse-ETL entry in the cache pipeline; must stop CRM before bootstrap.
- CRM's `wh_order_hdr` is baked in image — `order_discount_rate` needs docker rebuild if added to that view.

---

## Resolved Decisions

1. **Both margin metrics needed** — `avg_gross_margin_pct` (gross, pre-Shopee-fees) and `avg_order_contribution_margin_pct` (contribution, post-Shopee-fees) serve different surfaces. Both belong in `dim_customers`.

2. **`is_high_cancel_risk` stays Python-only** — two different thresholds (10% badge, 50% action trigger) serve different purposes; adding a warehouse column forces a choice that creates drift risk with no Metabase use case.

3. **`mart_order_cogs_summary` daily cadence** — COGS data changes only on pipeline refresh, not real-time; daily sync is sufficient.
