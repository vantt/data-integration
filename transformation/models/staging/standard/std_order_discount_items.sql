{{ config(
    materialized='view',
    tags=['standard', 'orders', 'discounts']
) }}

-- =================================================================================================
-- HOP: STANDARD ORDER DISCOUNT ITEMS - v2.0
-- =================================================================================================
-- Thin pass-through over stg_sapo_order_discount_items.
-- Grain: 1 row per discount item per order (order_id × discount_source × reason).
-- Adds source lineage columns (source_system, source_version).
-- No column renames — faithful to stg output (P0 gate; renames are Phase 1+).
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_order_discount_items') }}
)

SELECT
    order_id,
    order_code,
    created_at,
    discount_source,
    discount_rate,
    discount_value,
    amount,
    reason,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' AS source_system,
    'v2'   AS source_version

FROM source_data
