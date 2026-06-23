{{ config(
    tags=['mart', 'fact', 'inventory', 'snapshot'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- FACT: INVENTORY SNAPSHOT (Daily)
-- =============================================================================
-- Grain: 1 row per (variant_id, location_id, snapshot_date)
-- Materialization: external parquet, incremental append by snapshot_date
-- Retention: daily forever (~2,046 rows/day × 365 = ~750K rows/year)
--
-- Source: int_sapo_inventories (enriched inventory view from nightly batch)
-- snapshot_date = date of the nightly Sapo product batch run (3am ICT)
--
-- CAVEATS:
--   1. Sapo inventory.modified_on is always NULL — no intra-day change detection.
--      This is a daily snapshot only; real-time inventory needs webhook handler.
--   2. Only 3 physical locations appear (452566, 494912, 624127).
--      TheHealthyUs (639290) and ShowroomVVT (657377) are logical entities with
--      no inventory payload from Sapo API.
--   3. MM Market An Phú (624127) can have negative on_hand (consignment — stock
--      already shipped to partner; committed > on_hand is expected behavior).
--   4. Incremental dedup: if dbt runs multiple times on the same day, the
--      QUALIFY window keeps only 1 row per (variant_id, location_id, snapshot_date)
--      using the latest source_timestamp.
-- =============================================================================

WITH
{% if is_incremental() %}
already_loaded AS (
    SELECT DISTINCT snapshot_date FROM {{ this }}
),
{% endif %}

source AS (
    SELECT
        variant_id,
        product_id,
        sku,
        location_id,
        location_name,
        location_code,
        on_hand,
        available,
        committed,
        incoming,
        onway,
        min_value,
        max_value,
        mac,
        bin_location,
        wait_to_pack,
        inventory_modified_at,
        source_timestamp,
        snapshot_date
    FROM {{ ref('int_sapo_inventories') }}
    {% if is_incremental() %}
    -- Only ingest snapshots for dates not yet in the table
    WHERE snapshot_date NOT IN (SELECT snapshot_date FROM already_loaded)
    {% endif %}
),

-- Dedup: if batch ran more than once in a day, keep latest source_timestamp per grain
deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY variant_id, location_id, snapshot_date
            ORDER BY source_timestamp DESC
        ) AS rn
    FROM source
),

products AS (
    SELECT
        variant_id,
        product_key,
        product_id,
        product_name,
        category,
        category_code,
        brand_name,
        brand_code
    FROM {{ ref('dim_products') }}
    WHERE product_key != {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
)

SELECT
    -- Surrogate key
    {{ dbt_utils.generate_surrogate_key([
        'cast(d.variant_id as string)',
        'cast(d.location_id as string)',
        'cast(d.snapshot_date as string)'
    ]) }}                                           AS inventory_snapshot_key,

    -- Natural keys
    d.variant_id,
    d.location_id,
    d.snapshot_date,

    -- Product attributes (denormalized for query convenience)
    p.product_key,
    d.sku,
    p.product_id,
    p.product_name,
    p.category,
    p.category_code,
    p.brand_name,
    p.brand_code,

    -- Location attributes
    d.location_name,
    d.location_code,

    -- Stock levels
    d.on_hand,
    d.available,
    d.committed,
    d.incoming,
    d.onway,

    -- Reorder thresholds
    d.min_value,
    d.max_value,

    -- Cost basis (Moving Average Cost from Sapo)
    d.mac,

    -- Derived stock value
    CASE
        WHEN d.mac IS NOT NULL AND d.on_hand > 0
        THEN ROUND(d.on_hand * d.mac, 2)
        ELSE 0
    END                                             AS stock_value_at_mac,

    CASE
        WHEN d.mac IS NOT NULL AND d.committed > 0
        THEN ROUND(d.committed * d.mac, 2)
        ELSE 0
    END                                             AS committed_value_at_mac,

    -- Operational
    d.bin_location,
    d.wait_to_pack,

    -- Metadata
    d.inventory_modified_at,
    d.source_timestamp

FROM deduped d
LEFT JOIN products p
    ON CAST(d.variant_id AS VARCHAR) = CAST(p.variant_id AS VARCHAR)
WHERE d.rn = 1
ORDER BY d.snapshot_date DESC, d.location_id, d.sku
