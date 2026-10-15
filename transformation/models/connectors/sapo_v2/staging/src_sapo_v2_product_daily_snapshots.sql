{{ config(
    materialized='incremental',
    unique_key=['_dlt_load_id', 'entity_id'],
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo', 'products', 'history']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO PRODUCT DAILY SNAPSHOTS (nightly full capture)
-- =================================================================================================
-- One row per (capture run, product) from sapo_v2_raw/product_daily_snapshot. Every capture is
-- kept: this table is the extracted history, rebuilt in full from raw by a full refresh.
--   - captured_at / capture_run_id: one value per capture run (UTC run start).
--   - variants_json: compact variants array {id, sku, variant_prices, inventories}; payload is
--     discarded after extraction.
-- Incremental: only loads newer than the max _dlt_load_id already present.
-- The raw table may not exist yet (no capture on this lake): source_or_empty() then yields no row.
-- =================================================================================================

{% set existing_cols = (adapter.get_columns_in_relation(this) | map(attribute='name') | list) if is_incremental() else [] %}

WITH raw_data AS (
    SELECT
        entity_id,
        captured_at,
        capture_run_id,
        modified_on,
        payload_hash,
        payload,
        _dlt_load_id
    FROM {{ source_or_empty('sapo_v2_raw', 'product_daily_snapshot', [
        ['entity_id', 'VARCHAR'],
        ['captured_at', 'TIMESTAMPTZ'],
        ['capture_run_id', 'VARCHAR'],
        ['modified_on', 'VARCHAR'],
        ['payload_hash', 'VARCHAR'],
        ['payload', 'VARCHAR'],
        ['_dlt_load_id', 'VARCHAR'],
    ]) }} AS raw
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    WHERE _dlt_load_id > (SELECT COALESCE(MAX(_dlt_load_id), '') FROM {{ this }})
    {% endif %}
)

SELECT
    entity_id,
    json_extract_string(payload, '$.id')                  AS product_id,
    CAST(captured_at AS TIMESTAMPTZ)                      AS captured_at,
    capture_run_id,
    try_cast(modified_on AS TIMESTAMPTZ)                  AS modified_on,
    payload_hash,
    _dlt_load_id,
    json_extract_string(payload, '$.variants')            AS variants_json
FROM raw_data
-- a package loaded twice keeps one row per product and capture
QUALIFY ROW_NUMBER() OVER (PARTITION BY _dlt_load_id, entity_id ORDER BY capture_run_id) = 1
