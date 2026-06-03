{{ config(
    tags=['mart', 'dim', 'products'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- DIM: PRODUCTS
-- =============================================================================
-- Single product dimension. One row per (product_id, variant_id).
-- grain: variant_id (Sapo variant = the sellable unit with its own SKU).
--
-- Source priority:
--   1. PRIMARY — Sapo product catalog (stg_sapo_variants + stg_sapo_products)
--      Covers 558 products / ~679 unique SKUs.
--   2. FALLBACK — order_items (std_order_items) for any variant_id NOT in catalog.
--      Preserves legacy SKUs (SHA1, COR1, CB.3BLACK, etc.) from historical orders.
--
-- New columns vs old dim_products (backward-compatible; old cols preserved):
--   packsize_root_sku, packsize_quantity, barcode, unit, weight_grams,
--   last_seen_at, is_packsize, is_active_status,
--   category, category_code, brand_id, brand_name (from catalog),
--   misa_join_key, misa_qty_multiplier (from dim_sku_alias),
--   product_source ('catalog' | 'order_items' | 'unknown')
--
-- MISA join improvement:
--   mart_sku_economics_monthly joins: int_misa_sales_lines.product_code = dim_products.sku
--   After this rebuild, MISA direct-match coverage: ~11% → ~90%.
--   Additional coverage via misa_join_key for packsize variants.
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- Catalog source: variant-level attributes from Sapo API
-- ---------------------------------------------------------------------------
variants AS (
    SELECT * FROM {{ ref('std_variants') }}
),

products AS (
    SELECT * FROM {{ ref('std_products') }}
),

brands AS (
    SELECT * FROM {{ ref('ref_brands') }}
),

-- Alias mart: packsize → base SKU + MISA override
sku_alias AS (
    SELECT * FROM {{ ref('dim_sku_alias') }}
),

-- Resolve packsize_root_sku via self-join (fallback when Sapo doesn't populate root_sku)
base_variants AS (
    SELECT
        variant_id,
        sku AS root_sku,
        unit AS root_unit
    FROM variants
    WHERE is_packsize = false OR is_packsize IS NULL
),

-- Join variants to product-level attributes
catalog_raw AS (
    SELECT
        v.variant_id,
        v.sku,
        v.barcode,
        v.variant_name,
        v.variant_status,
        v.is_sellable,
        v.unit,
        v.weight_value::FLOAT                       AS weight_grams,
        v.retail_price::FLOAT                       AS last_sold_price,
        v.is_packsize,
        COALESCE(
            v.packsize_root_sku,
            bv.root_sku
        )                                           AS packsize_root_sku,
        COALESCE(
            v.packsize_root_sku,
            bv.root_sku
        )                                           AS packsize_root_unit_sku,
        v.packsize_quantity::FLOAT                  AS packsize_quantity,
        -- Product-level attributes from stg_sapo_products
        p.product_id,
        p.product_name,
        p.product_type,
        p.brand_id,
        p.brand                                     AS catalog_brand,
        p.category,
        p.category_code,
        p.is_medicine,
        p.tags,
        p.product_status,
        -- Timestamps
        GREATEST(v.modified_at, p.modified_at)      AS last_seen_at,
        'catalog'                                   AS product_source
    FROM variants v
    INNER JOIN products p
        ON v.product_id = p.product_id
    LEFT JOIN base_variants bv
        ON CAST(v.packsize_root_id AS VARCHAR) = CAST(bv.variant_id AS VARCHAR)
    WHERE v.variant_id IS NOT NULL
      AND v.sku IS NOT NULL
),

-- Apply brand normalization (seed wins over catalog brand string)
catalog_branded AS (
    SELECT
        c.*,
        COALESCE(b.brand_name, c.catalog_brand)     AS brand_name,
        b.brand_code
    FROM catalog_raw c
    LEFT JOIN brands b ON UPPER(c.catalog_brand) = UPPER(b.vendor_raw)
),

-- Apply SKU alias: get misa_join_key + misa_qty_multiplier for packsize variants
catalog_aliased AS (
    SELECT
        cb.*,
        COALESCE(sa.misa_join_key, cb.sku)          AS misa_join_key,
        COALESCE(sa.misa_qty_multiplier, 1)         AS misa_qty_multiplier
    FROM catalog_branded cb
    LEFT JOIN sku_alias sa ON cb.sku = sa.sapo_pack_sku
),

-- Final catalog CTE with surrogate key + dedup
-- Variants can appear multiple times because src_sapo_products holds multiple
-- snapshots per product_id (history_log + batch_sync). Latest wins.
catalog_final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(["product_id || '-' || coalesce(variant_id, '')"]) }}
                                                    AS product_key,
        product_id,
        variant_id,
        sku,
        barcode,
        product_name,
        variant_name,
        product_type,
        brand_name,
        brand_code,
        unit,
        weight_grams,
        last_sold_price,
        last_seen_at,
        category,
        category_code,
        brand_id,
        is_packsize,
        packsize_root_sku,
        packsize_quantity,
        (product_status = 'active')                 AS is_active_status,
        misa_join_key,
        misa_qty_multiplier,
        product_source
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY product_id, COALESCE(variant_id, '')
                ORDER BY last_seen_at DESC NULLS LAST
            ) AS rn
        FROM catalog_aliased
    )
    WHERE rn = 1
),

-- ---------------------------------------------------------------------------
-- Fallback source: order_items for variant_ids NOT in the catalog
-- Preserves legacy SKUs from historical orders (SHA1, COR1, etc.)
-- ---------------------------------------------------------------------------
order_items AS (
    SELECT * FROM {{ ref('std_order_items') }}
    WHERE product_id IS NOT NULL
      AND product_name IS NOT NULL
),

-- Dedup order_items: last record wins per (product_id, variant_id)
order_items_deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id
            ORDER BY extracted_at DESC
        ) AS rn
    FROM order_items
),

-- Only take order_items rows for variant_ids missing from catalog
fallback_variants AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(["product_id || '-' || coalesce(variant_id, '')"]) }}
                                                    AS product_key,
        oi.product_id,
        oi.variant_id,
        oi.sku,
        oi.barcode,
        oi.product_name,
        oi.variant_name,
        oi.product_type,
        COALESCE(b.brand_name, oi.vendor)           AS brand_name,
        b.brand_code,
        oi.unit,
        oi.weight_grams::FLOAT                      AS weight_grams,
        oi.unit_price::FLOAT                        AS last_sold_price,
        oi.extracted_at                             AS last_seen_at,
        -- New columns — NULL for fallback rows (no catalog data)
        CAST(NULL AS VARCHAR)                       AS category,
        CAST(NULL AS VARCHAR)                       AS category_code,
        CAST(NULL AS VARCHAR)                       AS brand_id,
        CAST(NULL AS BOOLEAN)                       AS is_packsize,
        CAST(NULL AS VARCHAR)                       AS packsize_root_sku,
        CAST(NULL AS FLOAT)                         AS packsize_quantity,
        CAST(NULL AS BOOLEAN)                       AS is_active_status,
        oi.sku                                      AS misa_join_key,
        1                                           AS misa_qty_multiplier,
        'order_items'                               AS product_source
    FROM order_items_deduped oi
    LEFT JOIN brands b ON UPPER(oi.vendor) = UPPER(b.vendor_raw)
    WHERE oi.rn = 1
      -- Only variants NOT already covered by catalog
      AND oi.variant_id NOT IN (SELECT variant_id FROM catalog_final WHERE variant_id IS NOT NULL)
)

-- ---------------------------------------------------------------------------
-- UNION: catalog (primary) + fallback order_items + Unknown sentinel
-- ---------------------------------------------------------------------------
SELECT * FROM catalog_final

UNION ALL

SELECT * FROM fallback_variants

UNION ALL

-- Unknown sentinel row — preserves FK integrity for orders with no product match
SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}   AS product_key,
    'Unknown'                                               AS product_id,
    'Unknown'                                               AS variant_id,
    'Unknown'                                               AS sku,
    'Unknown'                                               AS barcode,
    'Unknown'                                               AS product_name,
    'Unknown'                                               AS variant_name,
    'Unknown'                                               AS product_type,
    'Unknown'                                               AS brand_name,
    CAST(NULL AS VARCHAR)                                   AS brand_code,
    'Unknown'                                               AS unit,
    0                                                       AS weight_grams,
    0                                                       AS last_sold_price,
    CAST(NULL AS TIMESTAMPTZ)                               AS last_seen_at,
    CAST(NULL AS VARCHAR)                                   AS category,
    CAST(NULL AS VARCHAR)                                   AS category_code,
    CAST(NULL AS VARCHAR)                                   AS brand_id,
    CAST(NULL AS BOOLEAN)                                   AS is_packsize,
    CAST(NULL AS VARCHAR)                                   AS packsize_root_sku,
    CAST(NULL AS FLOAT)                                     AS packsize_quantity,
    CAST(NULL AS BOOLEAN)                                   AS is_active_status,
    'Unknown'                                               AS misa_join_key,
    1                                                       AS misa_qty_multiplier,
    'unknown'                                               AS product_source
