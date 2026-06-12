# Product Intermediate Models — Author Report

**Date:** 2026-06-12 · **Plan:** 260612-1059-product-health-analytics

## Models authored

### 1. `int_product_velocity_trend`
`transformation/models/marts/core/intermediate/int_product_velocity_trend.sql`

- **Config:** `materialized='table'`, `tags=['mart','intermediate']`, no `location()` — matches golden sample.
- **Sources:** `mart_sku_economics_monthly` (ref, not direct table).
- **Logic:** `latest_month` CTE uses `MAX(snapshot_month)` — no hardcoded date. `trailing_3m` = rows where `snapshot_month >= max_month - INTERVAL 2 MONTH`. `velocity_90d` = AVG over trailing 3 snapshots; `velocity_30d` = MAX FILTER on latest-month row. `velocity_momentum` is NULL when `trailing_months < 3`.
- **Output columns (contract):** `product_key`, `velocity_90d DOUBLE`, `velocity_30d DOUBLE`, `velocity_momentum VARCHAR`, `first_sale_month DATE`, `months_active INT`.

### 2. `int_product_discount_dependency`
`transformation/models/marts/core/intermediate/int_product_discount_dependency.sql`

- **Config:** same as above.
- **Source:** `fact_sales` (ref). `discount_amount` and `net_revenue` confirmed present; gross proxy = `net_revenue + discount_amount` (VAT-exclusive net + pre-discount amount).
- **Logic:** single aggregation over full `fact_sales` history. NULLIF on gross prevents division-by-zero. `discount_dependency` NULL when no gross.
- **Output columns (contract):** `product_key`, `discount_share DOUBLE`, `discount_dependency VARCHAR`.

## Validation (read-only against `sapo_export_latest.duckdb`)

### int_product_velocity_trend
| Metric | Value |
|---|---|
| Row count | 27 |
| Source products in `sku_economics` | 42 (27 have trailing-window data) |
| Momentum: ACCELERATING | 4 |
| Momentum: DECELERATING | 4 |
| Momentum: STABLE | 5 |
| Momentum: NULL (< 3 trailing months) | 14 |
| NULLs in `velocity_30d` | 7 (inactive in latest month) |

Note: 42 distinct products in `sku_economics`; 27 appear in the trailing 3-month window (15 had no sales in last 3 months → excluded from velocity_agg via trailing_3m CTE, so row count = 27 not 42). The downstream `mart_product_health` should LEFT JOIN to handle products absent from this model.

### int_product_discount_dependency
| Metric | Value |
|---|---|
| Row count | 104 |
| PROMO_HEAVY (>40%) | 11 |
| PROMO_LIGHT (>10–40%) | 26 |
| FULL_PRICE (≤10%) | 48 |
| NULL (no gross proxy) | 19 |
| Total discount / Total gross | ~13.2% (blended) |

## Proposed schema.yml blocks

```yaml
- name: int_product_velocity_trend
  description: >
    Product-level velocity trend and lifecycle dates. Grain: one row per product_key
    present in mart_sku_economics_monthly trailing window. velocity_momentum is NULL
    for products with < 3 trailing monthly snapshots.
  columns:
    - name: product_key
      tests:
        - not_null
        - unique
    - name: velocity_90d
      tests:
        - not_null
    - name: velocity_30d
      description: NULL when product had no sales in the latest snapshot month.
    - name: velocity_momentum
      description: "NULL = insufficient history (< 3 months). Values: ACCELERATING, STABLE, DECELERATING."
    - name: first_sale_month
      tests:
        - not_null
    - name: months_active
      tests:
        - not_null

- name: int_product_discount_dependency
  description: >
    Product-level discount dependency classification from fact_sales (full history).
    Grain: one row per product_key. discount_dependency is NULL for products with
    no gross proxy (zero net_revenue and zero discount_amount).
  columns:
    - name: product_key
      tests:
        - not_null
        - unique
    - name: discount_share
      description: NULL when no gross proxy. Otherwise [0, 1].
    - name: discount_dependency
      description: "NULL = no sales data. Values: PROMO_HEAVY, PROMO_LIGHT, FULL_PRICE."
```

## Caveats

1. **Coverage gap:** `int_product_velocity_trend` covers 27 of 42 sku_economics products (trailing-window only). 15 products with no sales in the last 3 months are excluded. `mart_product_health` must LEFT JOIN and treat NULLs as inactive/insufficient.
2. **velocity_30d NULLs:** 7 products appear in trailing_3m (older months) but have no latest-month row → velocity_90d is computed but velocity_30d = NULL → momentum = NULL via `trailing_months < 3` guard. Correct behavior.
3. **fact_sales grain:** discount_dependency covers 104 products (wider than sku_economics' 42). 19 NULLs are products with line rows but zero gross (fully-gifted or data quality). Acceptable — downstream can treat NULL as unknown.
4. **No circular ref:** both models read `mart_sku_economics_monthly` and `fact_sales` only — no reference to `mart_product_health` or each other.

---

**Status:** DONE
**Summary:** Both intermediate models authored, config matches golden sample, output contracts match spec. Validated by equivalent SELECT against standalone DB — row counts, momentum distribution, and discount dependency distribution confirmed reasonable.
**Concerns:** None blocking. Trailing-window coverage (27/42) is expected and documented; downstream mart must LEFT JOIN.
