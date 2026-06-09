# Phase 4 — Bundle/Composite Tracking: dim_bundle_components

> **Priority:** P4
> **Status:** DROPPED — 2026-06-09
> **Reason:** Sapo inventory transactions (`fact_inventory_movements`) đã có MAC cho mọi SKU kể cả bundle. Kế toán cũng không track COGS một số SKU trong MISA nên decompose bundle → MISA chỉ fix được một phần nhỏ. Giải pháp tốt hơn: thêm Sapo MAC fallback (`COALESCE(misa_cogs, sapo_mac_cogs)` + `cogs_source` column) trực tiếp vào `mart_sku_economics_monthly`.
> **Dependency:** Phase 1 (`dim_product_variants` must exist for FK references)

---

## Context Links

- Research: `plans/reports/research-260528-1654-sapo-product-schema-opportunities.md` §Composite Items
- Phase 1: `phase-01-foundational-fix.md`

---

## Overview

77 Sapo variants have `product_type = 'composite'` with a populated `composite_items` array. Each entry specifies a component SKU, quantity, and unit price at the time the bundle was created. This data enables:

1. **Correct COGS rollup for bundles** — currently bundles show NULL COGS in mart_sku_economics_monthly because their bundle SKU (e.g., `CB.3SHA`, `PVN150`) has no direct MISA invoice. Decomposing to components lets COGS flow from component MISA data.
2. **Promotion attribution per component** — which base products drive bundle sales volume?
3. **Bundle margin analysis** — bundle price vs sum(component COGS).

---

## Key Insights from Schema

- 77 composite variants across 77 products (`product_type = 'composite'`)
- 14 unique component SKUs appear across all bundles
- Most bundles = 1 component × N quantity (e.g., PVN150 = 2× VCST21004L001)
- Multi-component bundles are rare but exist (check `length(composite_items) > 1`)
- `sub_sku` = component's Sapo SKU → most are MISA-style codes → direct COGS lookup
- `price` field = component unit price at bundle creation time — can be stale vs current GIANHAP price; use as reference only

Sample composite_items record:
```json
{
  "sub_product_id": 49776380,
  "sub_variant_id": 72561096,
  "price": 2168000.0,
  "quantity": 2.0,
  "sub_product_type": "lots_date",
  "sub_sku": "VCST21004L001",
  "sub_name": "Thực phẩm bảo vệ sức khỏe Shark Cartilage Extract - Lọ",
  "medicine": false
}
```

---

## Requirements

### Functional
1. `dim_bundle_components` — 1 row per (bundle_variant_id, component_variant_id)
2. Bundle SKU + product name denormalized for readability
3. Component SKU + name + quantity per bundle
4. `bundle_component_cogs` computed as `component.import_price × quantity` (Sapo-side proxy; real COGS from MISA after Phase 1 join improves)
5. `is_misa_matched` flag — TRUE when component_sku is in MISA catalog (for coverage audit)

### Non-functional
- Pure unnest from `src_sapo_product_variants.composite_items_json` (Phase 1 staging model)
- No writes to existing models
- dbt tests: not_null(bundle_variant_id, component_sku), uniqueness on (bundle_variant_id, component_sku)

---

## Architecture

```
src_sapo_product_variants (Phase 1 — composite_items_json column)
    └── src_sapo_bundle_components (NEW staging — unnest composite_items)
            └── dim_bundle_components (NEW mart)
                    ↓
        mart_sku_economics_monthly (future: component COGS rollup to bundle SKU)
```

---

## Files to Create

### 1. `src_sapo_bundle_components.sql` (staging)

File: `transformation/models/staging/src_sapo_bundle_components.sql`

```sql
{{ config(
    materialized='view',
    tags=['source', 'sapo', 'products', 'bundles']
) }}

-- Unnests composite_items JSON array from src_sapo_product_variants.
-- Only includes variants with product_type = 'composite' and non-null composite_items_json.
-- One row per (bundle_variant_id, component position in array).

WITH base AS (
    SELECT
        variant_id      AS bundle_variant_id,
        sku             AS bundle_sku,
        product_id      AS bundle_product_id,
        product_name    AS bundle_product_name,
        UNNEST(
            TRY_CAST(composite_items_json AS JSON[])
        ) AS item
    FROM {{ ref('src_sapo_product_variants') }}
    WHERE product_type = 'composite'
      AND composite_items_json IS NOT NULL
)

SELECT
    bundle_variant_id,
    bundle_sku,
    bundle_product_id,
    bundle_product_name,

    -- Component fields
    json_extract_string(item, '$.sub_variant_id')   AS component_variant_id,
    json_extract_string(item, '$.sub_product_id')   AS component_product_id,
    json_extract_string(item, '$.sub_sku')          AS component_sku,
    json_extract_string(item, '$.sub_name')         AS component_name,
    json_extract_string(item, '$.quantity')         AS quantity,
    json_extract_string(item, '$.price')            AS component_unit_price,
    json_extract_string(item, '$.sub_product_type') AS component_product_type,
    json_extract_string(item, '$.medicine')         AS component_is_medicine
FROM base
```

### 2. `dim_bundle_components.sql` (mart)

File: `transformation/models/marts/products/dim_bundle_components.sql`

```sql
{{ config(
    tags=['mart', 'dim', 'products', 'bundles'],
    location="{{ get_rolling_location() }}"
) }}

-- Bundle decomposition dimension.
-- One row per (bundle_variant_id × component_sku).
-- Use to:
--   1. Roll up component COGS to bundle (JOIN on component_sku → int_misa_sales_lines.product_code)
--   2. Attribute bundle sales volume to component products
--   3. Compute bundle margin = bundle_price - SUM(component_cogs × quantity)
--
-- NOTE: component_unit_price is from bundle creation time — may be stale.
--       For current COGS, join component_sku → dim_product_variants.import_price.

WITH raw AS (
    SELECT * FROM {{ ref('src_sapo_bundle_components') }}
),

-- Get current import_price for each component from dim_product_variants (Phase 1)
component_prices AS (
    SELECT
        sku,
        import_price    AS current_import_price,
        retail_price    AS current_retail_price
    FROM {{ ref('dim_product_variants') }}
    WHERE is_packsize = false
),

-- Get MISA codes we know about (for is_misa_matched flag)
misa_codes AS (
    SELECT DISTINCT product_code
    FROM {{ ref('int_misa_sales_lines') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['bundle_variant_id', 'component_sku']) }} AS bundle_component_key,

    -- Bundle identity
    bundle_variant_id::BIGINT       AS bundle_variant_id,
    bundle_sku,
    bundle_product_id::BIGINT       AS bundle_product_id,
    bundle_product_name,

    -- Component identity
    component_variant_id::BIGINT    AS component_variant_id,
    component_product_id::BIGINT    AS component_product_id,
    component_sku,
    component_name,

    -- Quantity
    quantity::FLOAT                 AS quantity_per_bundle,

    -- Pricing (reference — from bundle creation time)
    component_unit_price::FLOAT     AS bundle_creation_unit_price,

    -- Current pricing from dim_product_variants (live)
    cp.current_import_price         AS component_current_import_price,
    cp.current_retail_price         AS component_current_retail_price,

    -- Computed COGS proxy: component COGS for this bundle
    -- Use current_import_price × quantity as Sapo-side COGS proxy
    -- True COGS = join component_sku → int_misa_sales_lines at mart query time
    ROUND(
        cp.current_import_price * raw.quantity::FLOAT,
        2
    )                               AS bundle_component_cogs_proxy,

    -- Coverage flag
    (mc.product_code IS NOT NULL)   AS is_misa_matched,

    component_product_type,
    component_is_medicine::BOOLEAN  AS component_is_medicine

FROM raw
LEFT JOIN component_prices cp ON raw.component_sku = cp.sku
LEFT JOIN misa_codes mc        ON raw.component_sku = mc.product_code
```

---

## Todo List

- [ ] Wait for Phase 1 `src_sapo_product_variants` to be created first
- [ ] Create `transformation/models/staging/src_sapo_bundle_components.sql`
- [ ] Create `transformation/models/marts/products/dim_bundle_components.sql`
- [ ] Create `transformation/models/marts/products/` directory if it doesn't exist
- [ ] Add schema.yml tests for dim_bundle_components
- [ ] Run: `dbt build --select +dim_bundle_components`
- [ ] Verify: 77 bundle variants, 14 unique component SKUs
- [ ] Verify: `is_misa_matched = true` for component SKUs like VCST21004L001, VCSC20001L001

---

## Tests Required

```yaml
models:
  - name: dim_bundle_components
    tests:
      - not_null: [bundle_variant_id, bundle_sku, component_sku, quantity_per_bundle]
      - unique: [{columns: [bundle_variant_id, component_sku]}]
    columns:
      - name: quantity_per_bundle
        tests:
          - dbt_utils.expression_is_true:
              expression: ">= 1"
```

---

## Downstream Use Cases

### 1. Bundle COGS rollup in mart_sku_economics_monthly (future enhancement)

After this phase, a bundle SKU's COGS can be computed as:
```sql
-- In mart_sku_economics_monthly, add a CTE:
bundle_cogs AS (
    SELECT
        dbc.bundle_sku,
        DATE_TRUNC('month', m.posting_date)::date AS snapshot_month,
        SUM(m.cogs_amount * dbc.quantity_per_bundle) AS bundle_cogs_amount
    FROM dim_bundle_components dbc
    JOIN int_misa_sales_lines m ON dbc.component_sku = m.product_code
    WHERE dbc.is_misa_matched = true
    GROUP BY dbc.bundle_sku, DATE_TRUNC('month', m.posting_date)::date
)
-- Then LEFT JOIN bundle_cogs into the final assembly on bundle_sku
```
This is a Phase 4b enhancement — Phase 4 only builds the dimension.

### 2. Promotion analysis
- "Which product families appear most in bundles?" → group by component_sku
- "Bundle attach rate" → join dim_bundle_components → fact_sales on bundle_sku → count orders

### 3. Dashboard: product_profitability
- Add "Bundle penetration" column: % of product's revenue coming from bundle SKUs
- Requires `product_inventory` blueprint rebuild (Phase 3)

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| UNNEST fails on empty `composite_items_json` | Low | WHERE composite_items_json IS NOT NULL |
| Multi-component bundles: duplicate rows | Low | unique test on (bundle_variant_id, component_sku) catches |
| component_unit_price stale vs current | Certain | Use current_import_price from dim_product_variants instead |
| Phase 1 `dim_product_variants` not yet built | High | Dependency gate: run Phase 1 first |

---

## Effort Estimate

- src_sapo_bundle_components: 30 min
- dim_bundle_components: 60 min
- Testing + verification: 30 min
- **Total: ~2h**
