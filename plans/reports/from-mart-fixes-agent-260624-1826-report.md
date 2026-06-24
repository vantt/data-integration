# Mart Fixes Agent Report — 260624-1826

## Task 1 — dim_customers: external materialization

### Before
```python
{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim'],
    post_hook=[
      "COPY (SELECT * FROM {{ this }}) TO '{{ get_rolling_location() }}' (FORMAT PARQUET)"
    ]
) }}
```
`post_hook` COPY runs after the DuckDB incremental merge. If the parquet file is locked at COPY time, dbt marks SUCCESS (incremental table updated) but the serving parquet stays stale — silent divergence.

### After
```python
{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}
```
Mirrors `dim_products`, `dim_channels`, `mart_product_health`, and every other external dim in the same dir. Write is atomic: dbt-duckdb writes the parquet then swaps the pointer — no partial-state window.

### Incremental dedup semantics
The `{% if is_incremental() %}` WHERE block (lines 253-261) is preserved in source but evaluates to `false` under `external` materialization — compiled SQL omits it. This is safe: `external` always does a full rebuild, producing all current rows from upstream sources (`dim_customers_base` + `int_customer_metrics` + `int_customer_economics`). The incremental guard was a DuckDB-table performance optimization, not a data-completeness guard. All columns preserved unchanged.

### dbt compile result
PASS — clean compile, no errors. Compiled SQL confirms no `{% if is_incremental() %}` block in output.

---

## Task 2 — mart_sku_economics_monthly: gross_margin_pct deprecation

### Consumer audit

| Surface | File(s) | References mart_sku_economics_monthly.gross_margin_pct? |
|---------|---------|--------------------------------------------------------|
| Blueprints (Metabase) | `product_profitability_cost.md` — the only blueprint querying `mart_sku_economics_monthly` | NO — uses `realized_margin_pct` throughout; `gross_margin_pct` appears only in `order_profitability_all.md` / `channel_p_l_deep_dive.md` / `finance_channel_pl.md` which query `fact_order_economics`, not the SKU mart |
| Rill | `rill/` | NO — no references found |
| CRM | `crm/` | `gross_margin_pct` used in multiple CRM files, but ALL read `foe.gross_margin_pct` from `fact_order_economics` (verified in `order_sql.py:26`, `customer_orders_sql.py:15`, `customer_dim_metrics_sql.py:23`) — not from the SKU mart |
| `mart_product_health.sql` | reads from `mart_sku_economics_monthly` | NO — selects only `realized_margin_pct` (line 44) |

**Result: zero BI/consumer references to `mart_sku_economics_monthly.gross_margin_pct` confirmed.**

### Before (lines 390-400)
```sql
        ROUND(
            COALESCE(
                mc.gross_profit * 100.0 / NULLIF(mc.misa_revenue_net, 0),
                (sa.net_revenue - smac.sapo_mac_cogs_amount) * 100.0
                    / NULLIF(sa.net_revenue, 0)
            ),
            4
        )                                                       AS gross_margin_pct,
```

### After
```sql
        -- DEPRECATED: column retained for schema compatibility; value intentionally NULL.
        -- Use realized_margin_pct instead (H010-corrected, Sapo net_revenue denominator).
        -- gross_margin_pct used MISA book revenue; H010 SKUs had uncorrected ~2× COGS error.
        -- Zero BI consumers confirmed (blueprints + rill + crm all use realized_margin_pct).
        CAST(NULL AS DOUBLE)                                    AS gross_margin_pct,
```
Column name retained (no schema break). Value is NULL. `schema.yml` already has `meta.deprecated: true` + `use_instead: realized_margin_pct` — no schema.yml change needed.

### dbt compile result
PASS — clean compile, no errors.

---

## Files changed
- `transformation/models/marts/core/dim_customers.sql`
- `transformation/models/marts/sales/mart_sku_economics_monthly.sql`

---

**Status:** DONE

**Per-task:**
1. `dim_customers` converted from `incremental` + `post_hook COPY` to `external` materialization — dbt compile PASS
2. `mart_sku_economics_monthly.gross_margin_pct` NULLed (zero consumers confirmed, schema name preserved) — dbt compile PASS

**Apply note:** Both models need `dbt run --select dim_customers mart_sku_economics_monthly`. `dim_customers` is now `external` — no `--full-refresh` flag needed or applicable (external always does a full parquet rewrite). Run order: `dim_customers` can run independently; `mart_sku_economics_monthly` has no dependency on `dim_customers`. After `dim_customers` first run under external, the old DuckDB incremental table (`main_marts.dim_customers`) will no longer be updated — only the parquet serving file will be written. Confirm with `bootstrap_serving_views.py` only if the DuckDB serving view needs to be repointed (likely not — view already points at the parquet path via `get_rolling_location()`).
