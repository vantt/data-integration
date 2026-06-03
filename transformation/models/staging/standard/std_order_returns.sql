{{ config(
    materialized='view',
    tags=['standard', 'returns']
) }}

-- =================================================================================================
-- HOP: STANDARD ORDER RETURNS - v2.0
-- =================================================================================================
-- Thin pass-through over stg_sapo_order_returns.
-- Grain: 1 row per return event (return_id).
-- Adds source lineage columns (source_system, source_version).
-- No column renames — faithful to stg output (P0 gate; renames are Phase 1+).
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_order_returns') }}
)

SELECT
    return_id,
    order_id,
    order_code,
    return_status,
    refund_status,
    return_reason,
    refund_amount,
    return_quantity,
    issued_at,
    received_at,
    created_at,
    modified_at,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' AS source_system,
    'v2'   AS source_version

FROM source_data
