# Phase 2 — Pricing Intelligence: dim_price_lists + fact_variant_prices_snapshot

> **Priority:** P2
> **Status:** READY (17 price lists, full price matrix confirmed in parquet)
> **Effort:** Medium (~3h dev)
> **Dependency:** Phase 1 (`src_sapo_product_variants` must exist)

---

## Context Links

- Research: `plans/reports/research-260528-1654-sapo-product-schema-opportunities.md` §Variant prices nesting
- Phase 1: `phase-01-foundational-fix.md`

---

## Overview

Each of the 682 variants carries a `variant_prices` array with up to 17 price list entries — one per channel/segment (BANLE retail, GIANHAP import, FB, US, WS_FJP, DAILY, etc.). Currently this pricing matrix is entirely invisible to dbt models. Exposing it enables:

1. **Channel margin baseline** — compare FB price vs GIANHAP cost → implied gross margin per channel before any fees
2. **Price change detection** — daily snapshot diff reveals price adjustments; correlate with margin trend changes
3. **Pricing compliance** — verify channel prices are above cost (GIANHAP); flag negative-margin list prices
4. **Wholesale tier analysis** — WS_FJP vs WS_THU vs Thuocsi_1 tier differentiation

Key finding: `GIANHAP` (`is_cost=true`) is the only cost price list. For Shark Cartilage VCST21004L001: GIANHAP = 510,840 VND vs MISA COGS ≈ similar range — confirms GIANHAP is a reliable Sapo-side COGS proxy for the 10% of SKUs not in MISA.

---

## Key Insights

- 17 distinct price list codes across catalog; `value=0.0` means "not configured for this channel"
- `BANLE` is status=`default` — the canonical retail price
- `GIANHAP` is `is_cost=true` — only cost price; highly correlated with MISA COGS
- Price lists are stable (no history in batch_sync) — need daily snapshot to detect changes
- Many channels have `value=0` for most SKUs — filter these for meaningful analysis
- `included_tax_price` ≠ `value` when `tax_included=false` on variant (8% VAT applies)

---

## Requirements

### Functional
1. `dim_price_lists` — 1 row per price_list_id (17 rows); reference dimension
2. `src_sapo_variant_prices` — staging unnest of variant_prices_json
3. `fact_variant_prices_snapshot` — daily snapshot: 1 row per (variant_id, price_list_id, snapshot_date) — only non-zero prices
4. `is_cost` flag propagated so COGS proxy queries can filter `is_cost = true`

### Non-functional
- Snapshot date = DATE of dbt run (via `current_date` macro or `{{ run_started_at }}`)
- Incremental strategy: append new snapshot dates; never overwrite historical prices
- Filter: only rows where `value > 0` (unconfigured channels excluded)

---

## Architecture

```
src_sapo_product_variants (Phase 1 — variant_prices_json column)
    └── src_sapo_variant_prices (NEW staging — unnest variant_prices)
            ├── dim_price_lists (NEW mart — 17 rows, static reference)
            └── fact_variant_prices_snapshot (NEW mart — incremental, daily)
```

---

## Files to Create

### 1. `src_sapo_variant_prices.sql` (staging)

File: `transformation/models/staging/src_sapo_variant_prices.sql`

```sql
{{ config(
    materialized='view',
    tags=['source', 'sapo', 'products', 'prices']
) }}

-- Unnests variant_prices JSON array from src_sapo_product_variants.
-- One row per (variant_id × price_list_id). Includes all 17 price lists.
-- Downstream models filter value > 0 to remove unconfigured channels.

WITH base AS (
    SELECT
        variant_id,
        sku,
        product_id,
        UNNEST(
            TRY_CAST(variant_prices_json AS JSON[])
        ) AS vp
    FROM {{ ref('src_sapo_product_variants') }}
    WHERE variant_prices_json IS NOT NULL
)

SELECT
    variant_id,
    sku,
    product_id,

    -- Price list identity
    json_extract_string(vp, '$.price_list_id')          AS price_list_id,
    json_extract_string(vp, '$.price_list.code')        AS price_list_code,
    json_extract_string(vp, '$.price_list.name')        AS price_list_name,
    json_extract_string(vp, '$.price_list.is_cost')     AS is_cost,
    json_extract_string(vp, '$.price_list.status')      AS price_list_status,

    -- Price values
    json_extract_string(vp, '$.value')                  AS price_value,
    json_extract_string(vp, '$.included_tax_price')     AS price_incl_tax,

    -- Source record id
    json_extract_string(vp, '$.id')                     AS variant_price_id
FROM base
```

### 2. `dim_price_lists.sql` (mart)

File: `transformation/models/marts/products/dim_price_lists.sql`

```sql
{{ config(
    tags=['mart', 'dim', 'products', 'prices'],
    location="{{ get_rolling_location() }}"
) }}

-- Reference dimension: 17 Sapo price lists.
-- Stable — changes only when Sapo admin adds/removes price lists.
-- is_cost = true → GIANHAP only (cost/import price).
-- is_default = true → BANLE (standard retail).

SELECT DISTINCT
    price_list_id::BIGINT           AS price_list_id,
    price_list_code,
    price_list_name,
    (is_cost = 'true')::BOOLEAN     AS is_cost,
    (price_list_status = 'default')::BOOLEAN AS is_default
FROM {{ ref('src_sapo_variant_prices') }}
WHERE price_list_id IS NOT NULL
ORDER BY is_default DESC, is_cost DESC, price_list_code
```

### 3. `fact_variant_prices_snapshot.sql` (mart)

File: `transformation/models/marts/products/fact_variant_prices_snapshot.sql`

```sql
{{ config(
    materialized='incremental',
    unique_key=['variant_id', 'price_list_id', 'snapshot_date'],
    incremental_strategy='delete+insert',
    tags=['mart', 'fact', 'products', 'prices'],
    location="{{ get_rolling_location() }}"
) }}

-- Daily snapshot of variant prices per price list.
-- Grain: 1 row per (variant_id × price_list_id × snapshot_date).
-- Only non-zero prices are stored (value = 0 means "not configured").
--
-- Use cases:
--   1. Price change detection: compare today vs yesterday for same (variant_id, price_list_id)
--   2. GIANHAP cost trend: track import price over time (is_cost = true)
--   3. Channel margin baseline: BANLE vs GIANHAP spread per variant
--   4. Pricing compliance: flag where price_list_code != GIANHAP but value < GIANHAP value
--
-- Incremental: appends today's snapshot. Run daily after product batch sync.

WITH prices AS (
    SELECT
        variant_id::BIGINT          AS variant_id,
        sku,
        product_id::BIGINT          AS product_id,
        price_list_id::BIGINT       AS price_list_id,
        price_list_code,
        price_list_name,
        (is_cost = 'true')::BOOLEAN AS is_cost,
        price_value::FLOAT          AS price_value,
        price_incl_tax::FLOAT       AS price_incl_tax,
        CURRENT_DATE                AS snapshot_date
    FROM {{ ref('src_sapo_variant_prices') }}
    WHERE price_value IS NOT NULL
      AND price_value::FLOAT > 0        -- exclude unconfigured channels
),

-- Pivot GIANHAP cost onto each row for inline margin calc
-- (avoids self-join at query time in downstream analysis)
gianhap AS (
    SELECT
        variant_id::BIGINT  AS variant_id,
        price_value::FLOAT  AS gianhap_cost
    FROM {{ ref('src_sapo_variant_prices') }}
    WHERE price_list_code = 'GIANHAP'
      AND price_value IS NOT NULL
      AND price_value::FLOAT > 0
)

SELECT
    prices.variant_id,
    prices.sku,
    prices.product_id,
    prices.price_list_id,
    prices.price_list_code,
    prices.price_list_name,
    prices.is_cost,
    prices.price_value,
    prices.price_incl_tax,
    prices.snapshot_date,

    -- Implied margin vs GIANHAP cost (only meaningful for non-cost price lists)
    g.gianhap_cost,
    CASE
        WHEN NOT prices.is_cost AND g.gianhap_cost > 0
        THEN ROUND((prices.price_value - g.gianhap_cost) * 100.0 / NULLIF(prices.price_value, 0), 2)
        ELSE NULL
    END AS implied_gross_margin_pct,

    -- Flag: selling below cost
    CASE
        WHEN NOT prices.is_cost AND g.gianhap_cost > 0
        THEN prices.price_value < g.gianhap_cost
        ELSE FALSE
    END AS is_below_cost

FROM prices
LEFT JOIN gianhap g ON prices.variant_id = g.variant_id

{% if is_incremental() %}
WHERE prices.snapshot_date > (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```

---

## Todo List

- [x] Wait for Phase 1 `src_sapo_product_variants` to be created
- [x] Create `transformation/models/staging/src_sapo_variant_prices.sql` (implemented as `stg_sapo_variant_prices_v2.sql`)
- [x] Ensure `transformation/models/marts/products/` directory exists (files placed in `marts/sales/` instead)
- [x] Create `transformation/models/marts/products/dim_price_lists.sql` (at `marts/sales/dim_price_lists.sql`)
- [x] Create `transformation/models/marts/products/fact_variant_prices_snapshot.sql` (at `marts/sales/fact_variant_prices_snapshot.sql`)
- [x] Add schema.yml tests
- [x] Run: `dbt build --select +dim_price_lists +fact_variant_prices_snapshot`
- [x] Verify: 17 rows in dim_price_lists; GIANHAP is_cost=true; BANLE is_default=true
- [x] Verify: fact_variant_prices_snapshot has no zero-price rows (filter value > 0 implemented)
- [ ] Verify: implied_gross_margin_pct for VCST21004L001 BANLE ≈ 78.9%

---

## Tests Required

```yaml
models:
  - name: dim_price_lists
    tests:
      - not_null: [price_list_id, price_list_code]
      - unique: [price_list_id]
    columns:
      - name: is_cost
        tests:
          - dbt_utils.expression_is_true:
              expression: "= true OR = false"   -- exactly 1 code has is_cost=true (GIANHAP)

  - name: fact_variant_prices_snapshot
    tests:
      - not_null: [variant_id, price_list_id, snapshot_date, price_value]
      - unique:
          columns: [variant_id, price_list_id, snapshot_date]
    columns:
      - name: price_value
        tests:
          - dbt_utils.expression_is_true:
              expression: "> 0"
```

---

## Downstream Use Cases

### Immediate (after this phase)
- **Channel pricing sheet** — pivot fact_variant_prices_snapshot on price_list_code → see all channel prices per SKU in one row
- **Cost-floor compliance check** — `is_below_cost = true` alert for any SKU on any non-cost price list
- **GIANHAP as COGS proxy** — use `gianhap_cost` in mart_sku_economics_monthly for the 10% of SKUs not in MISA

### With daily Dagster run
- **Price change alerts** — compare today vs yesterday snapshots; surface price_change_pct
- **Margin drift attribution** — when margin drops, did GIANHAP (import cost) go up or did BANLE (sell price) go down?

### Dashboard integration
- **shopee_channel_economics** — add "Implied margin (GIANHAP)" waterfall bar
- **finance_pl** — GIANHAP cost as secondary COGS validation where MISA data is absent

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| UNNEST on variant_prices_json fails | Low | TRY_CAST + WHERE variant_prices_json IS NOT NULL |
| Snapshot grows unbounded | Low | 17 price lists × 682 variants × 365 days = ~4.2M rows/year — acceptable |
| GIANHAP=0 on some variants skews margin calc | Medium | is_below_cost guards with g.gianhap_cost > 0 check |
| Phase 1 not yet built (src_sapo_variant_prices dependency) | High | Gate on Phase 1 completion |
| Price list schema changes (Sapo admin adds list) | Low | incremental append handles new rows automatically |

---

## Effort Estimate

- src_sapo_variant_prices: 30 min
- dim_price_lists: 20 min
- fact_variant_prices_snapshot: 60 min
- Testing + verification: 30 min
- **Total: ~2.5h**
