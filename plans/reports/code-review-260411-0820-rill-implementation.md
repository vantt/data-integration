# Rill Implementation Review

**Date:** 2026-04-11
**Verdict:** PARTIAL PASS — core structure correct, 2 critical issues, several missing spec items

---

## Design Spec Checklist

| # | Spec Item | Status | Notes |
|---|-----------|--------|-------|
| 1 | Repo structure `rill/` with `rill.yaml`, `connectors/`, `models/`, `metrics/`, `dashboards/` | PASS | Matches Section 7. Missing `reports/` dir (spec optional) |
| 2 | Source models reading `{{ .env.RILL_EXPORT_ROOT }}/<table>.parquet` with `materialize: true` | PASS | All 10 source YAMLs correct |
| 3 | Published datasets: all 10 tables | PASS | `publish_rill_assets.py` DEFAULT_TABLES matches spec exactly |
| 4 | SQL model: `orders_enriched` | PASS with issues | See Critical #1 below |
| 5 | SQL model: `sales_items_enriched` | PASS | Joins, columns, derived fields match spec |
| 6 | SQL model: `marketing_spend_enriched` | PASS with note | Branch join is indirect via `dim_channels.location_id` |
| 7 | SQL model: `targets_enriched` | MISSING | Not implemented |
| 8 | SQL model: `actual_vs_target_daily` | MISSING | Not implemented |
| 9 | Metrics: `orders_core_metrics` | PASS | All dimensions + measures match spec |
| 10 | Metrics: `sales_items_core_metrics` | PASS | Matches spec; extra dims `district`, `staff_name` beyond spec (fine) |
| 11 | Metrics: `marketing_spend_core_metrics` | PASS | All measures match spec |
| 12 | Metrics: `actual_vs_target_core_metrics` | MISSING | Blocked by missing `actual_vs_target_daily` model |
| 13 | Derived: `orders_exec_metrics` | MISSING | Design spec Section 6.5 |
| 14 | Derived: `orders_ops_metrics` | MISSING | Design spec Section 6.5 |
| 15 | Derived: `orders_staff_metrics` | MISSING | Design spec Section 6.5 |
| 16 | Dagster asset depends on `sapo_serving_db` | PASS | `deps=[sapo_serving_db]` in `rill.py` |
| 17 | Dagster asset calls `publish_rill_assets.py` | PASS | Subprocess call with timeout |
| 18 | `publish_rill_assets.py` copies to `export/rill/current/` | PASS | Atomic copy with manifest |
| 19 | Dagster loads rill module | PASS | `definitions.py` imports `rill` in `load_assets_from_modules` |
| 20 | Docker compose: rill service on `caddy_net` | PASS | Port 9009, correct mounts, `rill.lan.fwg.vn` label |
| 21 | `.env.example` in rill project | MISSING | Spec Section 7 mentions it |
| 22 | Explore dashboards (3) | PASS | `orders_core`, `sales_items_core`, `marketing_spend_core` |

---

## Critical Issues

### C1: TIMESTAMPTZ stripped to naive TIMESTAMP in `orders_enriched.sql`

**File:** `rill/models/orders_enriched.sql` line 3

```sql
CAST(o.order_timestamp AS TIMESTAMP) AS order_timestamp,
```

`fact_orders.order_timestamp` is `created_at` which originates as TIMESTAMPTZ. Casting to naive TIMESTAMP drops timezone info. Per project convention (see agent memory), this causes wrong display and wrong `date_key` derivation for orders between 0h-7h Vietnam time.

**Impact:** `order_date`, `hour_start`, `order_hour`, `day_of_week` all derived from this cast. Orders placed 00:00-06:59 VN time could show on wrong date.

**Fix:** Remove the cast entirely or cast to `TIMESTAMPTZ`:
```sql
o.order_timestamp,  -- keep TIMESTAMPTZ as-is
```
Same issue on line 35 with `first_shipped_at`.

### C2: TIMESTAMPTZ also stripped in `sales_items_enriched.sql`

**File:** `rill/models/sales_items_enriched.sql` line 3

```sql
CAST(s.sol_timestamp AS TIMESTAMP) AS sale_timestamp,
```

Same antipattern. `sale_date` and `sale_hour` will be wrong for early-morning transactions.

**Fix:** Remove the cast.

---

## Warnings

### W1: `rill.yaml` 5-minute global refresh cron may be aggressive

```yaml
models:
  refresh:
    cron: "*/5 * * * *"
    run_in_dev: true
```

Design doc Section 9 says Dagster should be the primary refresh controller, with Rill cron as fallback. 5-minute cron re-reads all 10 Parquet files every 5 minutes regardless of whether data changed. Consider `"0 * * * *"` (hourly) or removing `run_in_dev: true` for dev to avoid unnecessary I/O.

### W2: `marketing_spend_enriched.sql` branch join is fragile

```sql
LEFT JOIN src_dim_branch_location b ON c.location_id = CAST(b.branch_location_id AS VARCHAR)
```

`fact_marketing_spend` has no `branch_location_key`; the join goes through `dim_channels.location_id`. This works because `location_id` = `cast(id as string)` and `branch_location_id` = `cast(id as integer)` from the same source. But:
- Only works for channels that have `location_id` (generic/POS channels). Specific channels have `location_id = NULL`, so `branch_location_name` falls back to `'Unknown'` via COALESCE.
- Cross-type comparison (VARCHAR vs INTEGER cast to VARCHAR). Works in DuckDB but is implicit.

Not blocking but document the limitation.

### W3: `sales_items_core_metrics` missing `status` dimension from spec

Design spec Section 6.5 lists `status` as a recommended dimension. Implementation has it. Confirmed present.

Actually on re-check, `status` IS present in the implementation. This is fine.

### W4: `orders_enriched.sql` — `pending_gt_24h/48h` flags use `current_timestamp`

```sql
WHEN status = 'OPEN' THEN date_diff('hour', order_timestamp, current_timestamp) > 24
```

Since models are materialized, these flags freeze at materialization time. They won't update until the next refresh. With a 5-min cron this is mostly fine, but the semantics are "pending as of last refresh" not "pending right now." Acceptable tradeoff for materialized models.

### W5: `orchestration/assets/__init__.py` is empty but rill still loads

The `__init__.py` is `# Empty init` but `definitions.py` imports `rill` directly via `from orchestration.assets import ... rill`. This works because Python treats `rill.py` as a module. No issue, but noting it since the review was asked to check.

---

## Missing Items From Spec (Informational)

These are Phase 2+ items per the design doc rollout plan. Not blocking for initial deployment:

1. **`targets_enriched` SQL model** — Section 6.4 Model 4
2. **`actual_vs_target_daily` SQL model** — Section 6.4 Model 5
3. **`actual_vs_target_core_metrics`** — Section 6.5
4. **`orders_exec_metrics`** — derived metrics view
5. **`orders_ops_metrics`** — derived metrics view
6. **`orders_staff_metrics`** — derived metrics view
7. **`.env.example`** — Section 7 repo structure
8. **Canvas dashboards** — Section 6.2 mentions Rill should own these
9. **Reports/alerts** — Section 6.2

---

## Column Name Verification (Rill SQL vs dbt schema.yml)

| Rill Column Reference | dbt Source | Match? |
|---|---|---|
| `o.order_id` | `fact_orders.order_id` | YES |
| `o.order_code` | `fact_orders.order_code` | YES (implicit from SELECT *) |
| `o.order_timestamp` | `fact_orders.order_timestamp` (= `created_at`) | YES |
| `o.channel_key` | `fact_orders.channel_key` | YES |
| `o.branch_location_key` | `fact_orders.branch_location_key` | YES |
| `o.shipping_geography_key` | `fact_orders.shipping_geography_key` | YES |
| `o.staff_key` | `fact_orders.staff_key` | YES |
| `o.gross_revenue` | `fact_orders.gross_revenue` | YES |
| `o.net_revenue` | `fact_orders.net_revenue` | YES |
| `o.discount_amount` | `fact_orders.discount_amount` | YES |
| `o.tax_amount` | `fact_orders.tax_amount` | YES |
| `o.total_collected` | `fact_orders.total_collected` | YES |
| `o.first_shipped_at` | `fact_orders.first_shipped_at` | YES |
| `o.time_to_complete_hours` | `fact_orders.time_to_complete_hours` | YES |
| `o.status` | `fact_orders.status` (implicit) | YES |
| `o.payment_status` | `fact_orders.payment_status` (implicit) | YES |
| `o.fulfillment_status` | `fact_orders.fulfillment_status` (implicit) | YES |
| `c.channel_name` | `dim_channels.channel_name` | YES |
| `c.channel_category` | `dim_channels.channel_category` | YES |
| `c.platform` | `dim_channels.platform` | YES |
| `c.platform_group` | `dim_channels.platform_group` | YES |
| `c.is_sales_channel` | `dim_channels.is_sales_channel` | YES |
| `b.branch_location_name` | `dim_branch_location.branch_location_name` | YES |
| `g.geography_key` | `dim_geography.geography_key` | YES |
| `s.full_name` | `dim_staff.full_name` (implicit) | YES |
| `s.item_id` | `fact_sales.item_id` | YES |
| `s.sol_timestamp` | `fact_sales.sol_timestamp` | YES |
| `s.revenue` | `fact_sales.revenue` | YES |
| `s.discount_amount` | `fact_sales.discount_amount` | YES |
| `s.distributed_discount_amount` | `fact_sales.distributed_discount_amount` | YES |
| `p.product_name` | `dim_products.product_name` (implicit) | YES |
| `p.brand_name` | `dim_products.brand_name` | YES |
| `m.date_key` | `fact_marketing_spend.date_key` | YES |
| `m.spend_amount` | `fact_marketing_spend.spend_amount` | YES |
| `m.clicks` | `fact_marketing_spend.clicks` | YES |
| `m.impressions` | `fact_marketing_spend.impressions` | YES |

No column name mismatches found. All Rill SQL references resolve to real dbt mart columns.

---

## Positive Observations

- Atomic copy pattern in `publish_rill_assets.py` with manifest — good production hygiene
- Dagster timeout handling with `RILL_PUBLISH_TIMEOUT_SEC` env var
- Clean separation: source YAML models + SQL enrichment models + metrics views
- Docker compose mounts `.rill/` state to persistent host path
- `marketing_spend_enriched` correctly avoids ROAS/CAC claims (matches spec constraint)
- `orders_enriched` derives all specified flags, buckets, and timing helpers
- Metrics views use `filter (where ...)` syntax correctly for conditional aggregation

---

## Recommendations

1. **[Critical]** Remove `CAST(... AS TIMESTAMP)` in `orders_enriched.sql` lines 3, 35 and `sales_items_enriched.sql` line 3. Let TIMESTAMPTZ flow through.
2. **[Warning]** Change refresh cron from `*/5` to `0 *` (hourly) or disable `run_in_dev`.
3. **[Info]** Add `.env.example` to `rill/` with `RILL_EXPORT_ROOT` template.
4. **[Info]** Plan `targets_enriched` + `actual_vs_target_daily` as next iteration.
5. **[Info]** Plan derived metrics views (`orders_exec_metrics`, etc.) as follow-up.
