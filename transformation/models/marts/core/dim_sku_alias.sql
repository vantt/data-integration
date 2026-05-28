{{ config(
    tags=['mart', 'dim', 'sku', 'products'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- DIM: SKU ALIAS
-- =============================================================================
-- Bridge table mapping multi-pack Sapo SKUs → base unit SKUs for MISA join.
-- Also handles cases where MISA uses a different code than the Sapo base SKU.
--
-- Two sources UNION-ed; MANUAL_OVERRIDE wins on conflict:
--
-- 1. AUTO_PACKSIZE: generated from Sapo's packsize_root_id metadata.
--    One row per packsize variant. Covers ~120 variants automatically.
--    misa_join_key = packsize_root_sku (base unit SKU, which MISA typically uses).
--    misa_qty_multiplier = packsize_quantity (for COGS rollup).
--    Zero maintenance: picks up new packs as Sapo catalog is updated.
--
-- 2. MANUAL_OVERRIDE: from seed_sku_alias_manual.csv.
--    Covers cases where MISA uses a DIFFERENT code than Sapo base SKU
--    (e.g. Metabo: MISA = VCSP20002G001 "Gói", Sapo base = VCSP20002H030 "Hộp").
--    ~10 entries, audited by business owner.
--
-- Usage in mart_sku_economics_monthly (future):
--   When Sapo fact_sales.sku has no direct MISA match, look up dim_sku_alias
--   to find the misa_join_key and apply misa_qty_multiplier for COGS apportionment.
-- =============================================================================

WITH
-- ---------------------------------------------------------------------------
-- Source 1: AUTO from Sapo packsize metadata
-- ---------------------------------------------------------------------------
variants AS (
    SELECT
        variant_id,
        sku,
        unit,
        is_packsize,
        packsize_quantity,
        packsize_root_id,
        packsize_root_sku,
        product_id
    FROM {{ ref('stg_sapo_variants') }}
),

-- Only base variants (non-packsize) as lookup for root SKU resolution
base_variants AS (
    SELECT
        variant_id,
        sku AS base_sku,
        unit AS base_unit
    FROM variants
    WHERE is_packsize = false OR is_packsize IS NULL
),

-- Packsize variants joined to their base variant
auto_aliases AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['v.sku']) }}   AS sku_alias_key,
        v.sku                                               AS sapo_pack_sku,
        v.unit                                              AS sapo_pack_unit,
        COALESCE(v.packsize_root_sku, b.base_sku)           AS sapo_base_sku,
        b.base_unit                                         AS sapo_base_unit,
        CAST(v.packsize_quantity AS INTEGER)                AS units_per_pack,
        COALESCE(v.packsize_root_sku, b.base_sku)           AS misa_join_key,
        CAST(v.packsize_quantity AS INTEGER)                AS misa_qty_multiplier,
        'AUTO_PACKSIZE'                                     AS alias_source,
        NULL                                                AS notes
    FROM variants v
    LEFT JOIN base_variants b
        ON CAST(v.packsize_root_id AS VARCHAR) = CAST(b.variant_id AS VARCHAR)
    WHERE v.is_packsize = true
      AND v.sku IS NOT NULL
),

-- ---------------------------------------------------------------------------
-- Source 2: MANUAL overrides from seed
-- ---------------------------------------------------------------------------
manual_aliases AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['sapo_pack_sku']) }}   AS sku_alias_key,
        sapo_pack_sku,
        sapo_pack_unit,
        sapo_base_sku,
        sapo_base_unit,
        CAST(units_per_pack AS INTEGER)                             AS units_per_pack,
        misa_join_key,
        CAST(misa_qty_multiplier AS INTEGER)                        AS misa_qty_multiplier,
        'MANUAL_OVERRIDE'                                           AS alias_source,
        notes
    FROM {{ ref('seed_sku_alias_manual') }}
),

-- ---------------------------------------------------------------------------
-- UNION: manual wins on conflict (dedup by sapo_pack_sku, manual takes priority)
-- ---------------------------------------------------------------------------
combined AS (
    SELECT * FROM manual_aliases
    UNION ALL
    SELECT a.*
    FROM auto_aliases a
    WHERE a.sapo_pack_sku NOT IN (SELECT sapo_pack_sku FROM manual_aliases)
)

SELECT
    sku_alias_key,
    sapo_pack_sku,
    sapo_pack_unit,
    sapo_base_sku,
    sapo_base_unit,
    units_per_pack,
    misa_join_key,
    misa_qty_multiplier,
    alias_source,
    notes
FROM combined
WHERE sapo_pack_sku IS NOT NULL
  AND misa_join_key IS NOT NULL
