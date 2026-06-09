# Phase 1 — Foundational Fix: dim_products + dim_product_variants + seed_sku_alias

> **Priority:** P0 — Blocks all downstream analytics
> **Status:** READY (parquet readable; wait for ingestion fix before final run)
> **Effort:** Low (~3-4h dev)
> **Dependency:** `src_sapo_products.sql` must be fixed by other agent before `dbt build`

---

## Context Links

- Research: `plans/reports/research-260528-1654-sapo-product-schema-opportunities.md`
- MISA alignment: `plans/reports/research-260528-1608-misa-sapo-sku-alignment.md`
- Current dim_products: `transformation/models/marts/core/dim_products.sql`
- Current staging: `transformation/models/staging/src_sapo_products.sql`

---

## Overview

Replace order_items-only `dim_products` (105 SKUs) with a union of the new Sapo product catalog (558 products, 679 unique SKUs). Add:
- `dim_product_variants` — 1 row per variant_id (sub-product) with all variant-level attributes
- `dim_sku_alias` — bridge table for legacy codes (SHA1, COR1) → MISA codes
- `src_sapo_product_variants` — staging unnest of `variants_json` from `src_sapo_products`

The MISA join in `mart_sku_economics_monthly` uses `dim_products.sku = int_misa_sales_lines.product_code`. After this phase, **no changes to mart_sku_economics_monthly are needed** — the join hit rate improves automatically from 11.4% to 90.0%.

---

## Key Insights

- 501/679 Sapo SKUs follow MISA pattern (`VCS*...`) — direct match
- 181 of 201 MISA codes are present in the full catalog (90.0%)
- Remaining 20 unmatched MISA codes: 13 services (`DV*`/`CPBH`) + 7 discontinued products → these are acceptable gaps, not bugs
- `packsize=True` variants (120 total) are sub-packs of base variants — need `packsize_root_id` join to find base unit
- `cost_price` is NULL on all variants — use `variant_import_price` or GIANHAP price list as fallback COGS proxy
- `brand_id` + `brand` are on the product payload (not variants) — embed in dim_products
- All products have `status=active` (batch_sync fetches active catalog only)

---

## Requirements

### Functional
1. `dim_products` covers all 558 Sapo products (not just those with order history)
2. One row per `product_id × variant_id` — same grain as today
3. `sku` column = primary MISA join key (unchanged semantics, broader coverage)
4. Brand/category/type enriched from catalog (not just order_items)
5. Legacy `Unknown` sentinel row preserved for FK integrity
6. `dim_product_variants` has 1 row per `variant_id` with unit, packsize, weight, vat fields
7. `seed_sku_alias` maps short legacy codes to MISA codes with confidence + notes columns

### Non-functional
- Incremental-safe: new catalog rows replace stale order_item-derived rows (catalog wins)
- No breaking changes to downstream marts (dim_products columns preserved + new columns added)
- dbt tests pass: not_null(product_id, variant_id, sku), unique(variant_id)

---

## Architecture

```
src_sapo_products (incremental, 558 rows, 1 per product_id)
    └── src_sapo_product_variants (NEW, unnest variants_json → 682 rows)
            ├── dim_product_variants (NEW mart, 682 rows, 1 per variant_id)
            └── dim_products (MODIFIED: UNION catalog + order_items fallback)
                    └── dim_sku_alias (NEW mart, from seed_sku_alias.csv)
```

`mart_sku_economics_monthly` uses `dim_products.sku` as join key to MISA → auto-improves.

---

## Implementation Steps

### Step 1 — Create `src_sapo_product_variants.sql` (staging)

File: `transformation/models/staging/src_sapo_product_variants.sql`

Purpose: unnest `variants_json` from `src_sapo_products` into 1 row per variant.

```sql
{{ config(
    materialized='view',
    tags=['source', 'sapo', 'products', 'variants']
) }}

-- Unnests the variants_json array from src_sapo_products.
-- One row per variant_id. Extracts all scalar variant fields.
-- Nested arrays (variant_prices, inventories, composite_items) left as JSON text
-- for downstream unnest models (src_sapo_variant_prices, src_sapo_product_inventories).

WITH base AS (
    SELECT
        product_id,
        product_name,
        product_status,
        product_type,
        brand_id,
        brand,
        category_id,
        category,
        category_code,
        medicine,
        tags,
        created_on      AS product_created_on,
        modified_on     AS product_modified_on,
        -- unnest variant array
        UNNEST(
            TRY_CAST(variants_json AS JSON[])
        ) AS v
    FROM {{ ref('src_sapo_products') }}
    WHERE variants_json IS NOT NULL
)

SELECT
    product_id,
    product_name,
    product_status,
    product_type,
    brand_id,
    brand,
    category_id,
    category,
    category_code,
    medicine,
    tags,
    product_created_on,
    product_modified_on,

    -- Variant identity
    json_extract_string(v, '$.id')              AS variant_id,
    json_extract_string(v, '$.sku')             AS sku,
    json_extract_string(v, '$.barcode')         AS barcode,
    json_extract_string(v, '$.status')          AS variant_status,
    json_extract_string(v, '$.name')            AS variant_name,
    json_extract_string(v, '$.sellable')        AS sellable,

    -- Variant attributes
    json_extract_string(v, '$.unit')            AS unit,
    json_extract_string(v, '$.weight_value')    AS weight_value,
    json_extract_string(v, '$.weight_unit')     AS weight_unit,
    json_extract_string(v, '$.opt1')            AS opt1,
    json_extract_string(v, '$.opt2')            AS opt2,
    json_extract_string(v, '$.opt3')            AS opt3,

    -- Packsize (multi-unit pack link)
    json_extract_string(v, '$.packsize')        AS is_packsize,
    json_extract_string(v, '$.packsize_quantity')   AS packsize_quantity,
    json_extract_string(v, '$.packsize_root_id')    AS packsize_root_variant_id,

    -- Pricing shortcuts
    json_extract_string(v, '$.variant_retail_price')    AS retail_price,
    json_extract_string(v, '$.variant_import_price')    AS import_price,
    json_extract_string(v, '$.variant_whole_price')     AS wholesale_price,
    json_extract_string(v, '$.cost_price')              AS cost_price,

    -- VAT
    json_extract_string(v, '$.input_vat_rate')      AS input_vat_rate,
    json_extract_string(v, '$.output_vat_rate')     AS output_vat_rate,
    json_extract_string(v, '$.taxable')             AS taxable,
    json_extract_string(v, '$.tax_included')        AS tax_included,

    -- Expiry
    json_extract_string(v, '$.expiration_alert_time')   AS expiration_alert_days,

    -- Nested JSON arrays (kept as text for downstream unnest)
    json_extract_string(v, '$.variant_prices')      AS variant_prices_json,
    json_extract_string(v, '$.inventories')         AS inventories_json,
    json_extract_string(v, '$.composite_items')     AS composite_items_json,

    -- Timestamps
    json_extract_string(v, '$.created_on')          AS variant_created_on,
    json_extract_string(v, '$.modified_on')         AS variant_modified_on
FROM base
```

### Step 2 — Create `seed_sku_alias.csv`

File: `transformation/seeds/seed_sku_alias.csv`

Pre-fill known legacy → MISA mappings from research. Mark uncertain as `pending`. Business owner reviews and flips `pending` → `verified`.

```csv
sapo_sku,misa_product_code,confidence,notes
SHA1,VCST21004L001,pending,"Shark Cartilage vs Shark Cartilage Extract — likely same product, confirm with ops"
COR1,VCSC20001L001,pending,"Cordyceps — confirm with ops"
FU1,VCFB22119B001,pending,"Fine Fucoidan — check product code"
REI1,VTSC21006L001,pending,"Royal Reishi — check product code"
COL1,VCSL19001C001,pending,"Collagen — likely same as VCSL19001C001, confirm"
CORP.H,?,pending,"Đông trùng hạ thảo nước — no MISA match found; request code from finance"
COLY.H,?,pending,"Collagen Yến — no MISA match found; request code from finance"
ME1,?,pending,"Me1 product — identify MISA code"
NAT1,?,pending,"Natural product — identify MISA code"
```

### Step 3 — Create `dim_sku_alias.sql`

File: `transformation/models/marts/core/dim_sku_alias.sql`

```sql
{{ config(
    tags=['mart', 'dim', 'sku'],
    location="{{ get_rolling_location() }}"
) }}

-- Bridge table: legacy/short Sapo SKUs → canonical MISA product codes.
-- Used as a 3rd-tier join fallback in mart_sku_economics_monthly:
--   Tier 1: direct dim_products.sku = misa.product_code
--   Tier 2: fuzzy name normalization (see mart_sku_economics_monthly comments)
--   Tier 3: this alias table
--
-- Populated from seed_sku_alias.csv.
-- confidence = 'verified' | 'pending' — only 'verified' rows used in mart joins.
-- Do NOT auto-generate aliases without business owner review (false positive risk).

SELECT
    sapo_sku,
    misa_product_code,
    confidence,
    notes
FROM {{ ref('seed_sku_alias') }}
WHERE misa_product_code IS NOT NULL
  AND misa_product_code != '?'
```

### Step 4 — Create `dim_product_variants.sql`

File: `transformation/models/marts/core/dim_product_variants.sql`

```sql
{{ config(
    tags=['mart', 'dim', 'products', 'variants'],
    location="{{ get_rolling_location() }}"
) }}

-- One row per variant_id. Sub-product dimension.
-- Includes all variant-level attributes from Sapo product catalog.
-- Use dim_products (product_id grain) for product-level analysis.
-- Use this model for variant-level drill (unit, packsize, weight, pricing, VAT).

WITH variants AS (
    SELECT * FROM {{ ref('src_sapo_product_variants') }}
),

-- Resolve packsize_root: find base unit SKU for multi-pack variants
packsize_base AS (
    SELECT
        variant_id AS root_variant_id,
        sku        AS root_sku,
        unit       AS root_unit
    FROM variants
    WHERE is_packsize = 'false' OR is_packsize IS NULL
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['variant_id']) }} AS variant_key,

    -- Natural keys
    variant_id::BIGINT          AS variant_id,
    product_id::BIGINT          AS product_id,
    sku,
    barcode,

    -- Product attributes (denormalized)
    product_name,
    variant_name,
    brand,
    brand_id::BIGINT            AS brand_id,
    category,
    category_code,
    product_type,
    medicine::BOOLEAN           AS is_medicine,
    tags,

    -- Variant attributes
    unit,
    weight_value::FLOAT         AS weight_grams,    -- weight_unit is always 'g' in catalog
    opt1,

    -- Packsize
    (is_packsize = 'true')::BOOLEAN         AS is_packsize,
    packsize_quantity::FLOAT                AS packsize_quantity,
    packsize_root_variant_id::BIGINT        AS packsize_root_variant_id,
    pb.root_sku                             AS packsize_root_sku,
    pb.root_unit                            AS packsize_root_unit,

    -- Pricing (from variant top-level fields — not full price list)
    retail_price::FLOAT         AS retail_price,
    import_price::FLOAT         AS import_price,    -- GIANHAP equivalent
    wholesale_price::FLOAT      AS wholesale_price,

    -- VAT
    input_vat_rate::FLOAT       AS input_vat_rate,
    output_vat_rate::FLOAT      AS output_vat_rate,

    -- Expiry tracking
    expiration_alert_days::INT  AS expiration_alert_days,

    -- Timestamps
    TRY_CAST(variant_created_on AS TIMESTAMPTZ)     AS created_at,
    TRY_CAST(variant_modified_on AS TIMESTAMPTZ)    AS modified_at

FROM variants v
LEFT JOIN packsize_base pb
    ON v.packsize_root_variant_id = pb.root_variant_id::VARCHAR
WHERE v.variant_id IS NOT NULL
```

### Step 5 — Modify `dim_products.sql`

Strategy: **UNION** (1) the new Sapo catalog source (primary, wins) with (2) order_items fallback (for any variant_ids in orders not yet in the catalog).

**Key columns to add (new from catalog):**
- `brand_id`, `brand_name` (from catalog — not just ref_brands seed)
- `category`, `category_code`
- `is_packsize`, `packsize_quantity`, `packsize_root_variant_id`
- `input_vat_rate`, `output_vat_rate`
- `tags`, `is_medicine`
- `product_source` (`'catalog'` | `'order_items'`) — for audit

**Logic:**
```sql
-- Priority 1: Sapo product catalog (558 products, authoritative)
SELECT ... 'catalog' AS product_source
FROM src_sapo_product_variants

UNION ALL

-- Priority 2: order_items fallback (only variant_ids NOT in catalog)
SELECT ... 'order_items' AS product_source
FROM std_order_items
WHERE variant_id NOT IN (SELECT variant_id FROM src_sapo_product_variants)

-- Then QUALIFY/ROW_NUMBER to keep catalog version when both exist
```

**Columns preserved (no breaking changes):**
- `product_key`, `product_id`, `variant_id`, `sku`, `barcode`
- `product_name`, `variant_name`, `product_type`
- `brand_name`, `brand_code` (from ref_brands seed, supplemented by catalog)
- `unit`, `weight_grams`, `last_sold_price`
- `last_seen_at`
- `Unknown` sentinel row

---

## Todo List

- [x] Create `src_sapo_product_variants.sql` (implemented as `stg_sapo_variants_v2.sql`)
- [x] Create `seed_sku_alias.csv` with pre-filled known aliases (implemented as `seed_sku_alias_manual.csv`)
- [x] Create `dim_sku_alias.sql` (AUTO_PACKSIZE + AUTO_VTS_TO_VCS + MANUAL_OVERRIDE sources)
- [x] Create `dim_product_variants.sql` (merged into `dim_products.sql` with variant_id grain)
- [x] Modify `dim_products.sql` to union catalog + order_items (UNION catalog_final + fallback_variants + Unknown sentinel)
- [x] Add schema.yml tests (not_null, unique) for new models
- [x] Run: `dbt build --select +dim_products +dim_sku_alias`
- [x] Verify MISA hit rate: ~90% confirmed
- [x] Verify no downstream model breakage
- [ ] Request business owner review of seed_sku_alias_manual.csv `pending` entries

---

## Tests Required

```yaml
# In schema.yml for marts/core/
models:
  - name: dim_product_variants
    tests:
      - not_null: [variant_id, product_id, sku]
      - unique: [variant_id]
    columns:
      - name: variant_id
        tests: [not_null, unique]
      - name: sku
        tests: [not_null]

  - name: dim_products
    tests:
      - not_null: [product_key, sku]
      - unique: [product_key]

  - name: dim_sku_alias
    tests:
      - unique: [sapo_sku]

seeds:
  - name: seed_sku_alias
    columns:
      - name: sapo_sku
        tests: [not_null]
      - name: confidence
        tests:
          - accepted_values:
              values: ['verified', 'pending']
```

---

## Downstream Marts That Benefit (auto, no SQL change)

| Mart | Benefit |
|------|---------|
| `mart_sku_economics_monthly` | MISA COGS coverage: 32% → ~85% (rows), 18.7% → ~80-85% (revenue) |
| `product_performance` blueprint | All 558 SKUs appear, not just 105 |
| `shopee_channel_economics` | True margin on more SKUs |
| `finance_pl` blueprints | COGS attribution on ~90% of MISA codes |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `variants_json` UNNEST fails on edge cases | Low | Wrap with TRY_CAST + WHERE variant_id IS NOT NULL |
| Duplicate variant_id between catalog and order_items | Medium | QUALIFY to keep catalog version |
| dim_products column mismatch breaks downstream | Low | Preserve all existing columns, only ADD new ones |
| seed_sku_alias false positive (wrong alias) | Medium | Only verified=true rows used in join; pending rows visible for audit |
| dbt build with DuckDB lock from other agent | High (timing) | Do NOT run until agent af4df reports complete |

---

## Success Criteria

- `dim_products` row count ≥ 558 (catalog) + incremental order_item additions
- `dim_product_variants` has 682 rows, variant_id unique, sku not_null
- `mart_sku_economics_monthly` COGS coverage ≥ 75% of rows (from 32%)
- No failing dbt tests in marts/core/
- `dbt build --select +dim_products` completes without errors

---

## Effort Estimate

- Step 1 (src_sapo_product_variants): 45 min
- Step 2 (seed_sku_alias): 30 min
- Step 3 (dim_sku_alias): 20 min
- Step 4 (dim_product_variants): 60 min
- Step 5 (dim_products modify): 60 min
- Testing + verification: 45 min
- **Total: ~3.5h**
