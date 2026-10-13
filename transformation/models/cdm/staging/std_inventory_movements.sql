{{ config(
    materialized='view',
    tags=['standard', 'inventory']
) }}

-- =================================================================================================
-- STD: INVENTORY MOVEMENTS - v2.0
-- =================================================================================================
-- Source:  src_sapo_v2_inventory_transactions (table, ~32,957 deduped rows)
-- Grain:   1 row per inventory_movement_id (= entity_id content hash)
-- PK:      inventory_movement_id (surrogate = entity_id)
-- Natural key: (log_root_id, variant_id, location_id, issued_at_utc, onhand) — 0 collisions.
--
-- Key semantics:
--   quantity_delta = import_quantity − export_quantity (+IN / −OUT). Mutually exclusive.
--   movement_direction derived from import_quantity>0, NOT from action field.
--     (stock_transfer action='received' fires at BOTH ends; direction via import_quantity>0 — caveat #1)
--   cogs_amount = export_amount (pre-txn MAC cost; NOT export_qty × mac which is post-txn)
--   inventory_value = amount (= onhand × mac; verified 100% identity for mac>0 rows)
--   total_mac always 0 — dropped per analysis.
--
-- Dedup: QUALIFY ROW_NUMBER() on entity_id (business-grain dedup at std gate).
-- source_system = 'sapo_v2', source_version = 'v2'.
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_v2_inventory_transactions') }}
)

SELECT
    -- Surrogate PK (entity_id = content hash, perfectly unique)
    entity_id                                                           AS inventory_movement_id,

    -- Natural key components (0-collision composite key per analysis §6)
    log_root_id,
    variant_id,
    location_id,
    issued_at_utc,
    onhand,

    -- Signed quantity (import and export are mutually exclusive per row)
    -- quantity_delta: +IN (import), −OUT (export), 0 (catalog/cost-adjust rows)
    (COALESCE(import_quantity, 0) - COALESCE(export_quantity, 0))       AS quantity_delta,

    -- Direction derived from import_quantity>0 (NOT action field):
    --   stock_transfer action='received' fires at BOTH doc ends; import_quantity>0 identifies
    --   the receiving leg unambiguously — see analysis caveat #1.
    CASE
        WHEN import_quantity > 0 THEN 'IN'
        WHEN export_quantity > 0 THEN 'OUT'
        ELSE 'ZERO'
    END                                                                 AS movement_direction,

    -- COGS = export_amount (pre-txn MAC; using export_qty × mac would be post-txn, incorrect)
    export_amount                                                       AS cogs_amount,

    -- Inventory value = amount = onhand × mac (100% verified identity for mac>0 rows)
    amount                                                              AS inventory_value,

    -- Moving average cost at time of transaction (post-txn)
    mac                                                                 AS moving_avg_cost,

    -- Timestamptz (authoritative) and ICT business date
    issued_at_utc                                                       AS issued_at,
    CAST(issued_at_utc AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE)        AS issued_date_key,

    -- Document reference
    trans_object_code                                                   AS document_code,
    trans_object_id,

    -- Transaction classification
    trans_type,
    trans_type_name,
    log_type,
    log_type_name,

    -- Action verb (e.g. 'import', 'export', 'received') — informational; direction from import_qty
    action,

    -- Product & variant (denormalized from source; variant_id/location_id already selected above)
    product_id,
    product_name,
    product_category,
    variant_name,
    sku,
    barcode,
    unit,

    -- Location (denormalized from source; location_id already selected above)
    location_label,

    -- Raw quantities (kept for auditability)
    import_quantity,
    export_quantity,
    import_amount,

    -- Envelope metadata
    event_timestamp,

    -- Source provenance
    'sapo_v2'  AS source_system,
    'v2'    AS source_version

FROM source_data
-- Business-grain dedup at std gate: if entity_id dupes exist (27 re-fetch cases per analysis),
-- keep latest event_timestamp. entity_id is already unique in src_ but guard here defensively.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY event_timestamp DESC
) = 1
