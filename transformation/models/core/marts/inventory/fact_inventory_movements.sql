{{ config(
    tags=['mart', 'fact', 'inventory'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: INVENTORY MOVEMENTS
-- =================================================================================================
-- Source:  std_inventory_movements (VIEW, ~32,957 rows)
-- Grain:   1 row per inventory_movement_id (= entity_id content hash)
-- PK:      inventory_movement_id
--
-- Filter:  quantity_delta != 0 — excludes zero-qty catalog-init (trans_type=501) and
--          pure cost-adjustment rows (trans_type=600, 2 rows). Analysis caveat #2:
--          shipped_fulfillment_cancelled rows (1,064) are kept as-is — do NOT net/sum
--          cancellations; both IN and OUT legs are preserved for accurate ledger history.
--
-- Columns: faithful pass-through from std; no aggregation. One row = one ledger event.
-- =================================================================================================

WITH std AS (
    SELECT * FROM {{ ref('std_inventory_movements') }}
)

SELECT
    -- Primary key
    inventory_movement_id,

    -- Date/time (ICT business date + UTC timestamptz)
    issued_date_key,
    issued_at,

    -- Document reference
    document_code,

    -- Transaction classification
    trans_type,
    trans_type_name,

    -- Movement direction (IN/OUT derived from import_quantity>0; see std for caveat on stock_transfer)
    movement_direction,

    -- Product & variant (denormalized for BI query convenience)
    product_id,
    product_name,
    variant_id,
    variant_name,
    sku,

    -- Location
    location_id,
    location_label,

    -- Signed quantity: +IN / −OUT
    quantity_delta,

    -- Raw quantities (kept for drill-down)
    import_quantity,
    export_quantity,

    -- Cost / value
    cogs_amount,        -- export_amount: COGS at pre-txn MAC (use directly; do NOT recompute)
    inventory_value,    -- amount = onhand × mac (post-txn balance value)
    onhand,             -- running stock balance at moment of transaction (authoritative)
    moving_avg_cost,    -- mac: moving average cost per unit (post-txn)

    -- Provenance
    source_version

FROM std
WHERE quantity_delta != 0
