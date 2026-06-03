{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO INVENTORY TRANSACTIONS V2
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (batch_sync ingest, content-addressed entity_id).
--   2. Technical dedup ONLY by entity_id (ROW_NUMBER on event_timestamp + _dlt_load_id).
--      entity_id is a content hash — identical re-fetches collapse; any payload change
--      (incl. onhand running balance) produces a distinct entity_id. Therefore no
--      business-grain dedup here: that is deferred to the std layer (Phase 5).
--   3. Extract ALL scalar JSON fields from payload. Discard payload → OOM-safe.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - unique_key = entity_id (content hash); delete+insert replaces any re-fetched row.
--
-- Grain: 1 row per (document × product line × content-state).
-- onhand = running stock balance at moment of transaction.
-- import_amount / export_amount = stock-value movements (MAC-based).
-- mac = moving-average cost at transaction time; total_mac = cumulative MAC after txn.
-- =================================================================================================

{% set existing_cols = (adapter.get_columns_in_relation(this) | map(attribute='name') | list) if is_incremental() else [] %}

WITH
{% if is_incremental() %}
_cursor AS (
    {% if '_dlt_load_id' in existing_cols %}
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
    {% else %}
    SELECT '' AS max_load_id
    {% endif %}
),
{% endif %}
raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,
        payload
    FROM {{ source('sapo_raw', 'inventory_transaction_v2') }}
    {% if is_incremental() %}
    WHERE _dlt_load_id > (SELECT max_load_id FROM _cursor)
    {% endif %}
),

deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC NULLS LAST,
                _dlt_load_id DESC NULLS LAST
        ) AS rn
    FROM raw_data
),

-- Tech dedup + JSON extraction (payload discarded after this CTE)
-- No business dedup: entity_id IS the content key; std layer owns business-grain logic.
extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,

        -- Transaction timestamp (authoritative; also stored in event_timestamp envelope)
        try_cast(json_extract_string(payload, '$.issued_at_utc') AS TIMESTAMPTZ) AS issued_at_utc,

        -- Document / log identifiers
        try_cast(json_extract_string(payload, '$.log_root_id')     AS BIGINT)    AS log_root_id,
        try_cast(json_extract_string(payload, '$.log_type')        AS BIGINT)    AS log_type,
        json_extract_string(payload, '$.log_type_name')                          AS log_type_name,

        -- Transaction type
        try_cast(json_extract_string(payload, '$.trans_type')      AS BIGINT)    AS trans_type,
        json_extract_string(payload, '$.trans_type_name')                        AS trans_type_name,

        -- Source document (order, PO, adjustment, etc.)
        try_cast(json_extract_string(payload, '$.trans_object_id') AS BIGINT)    AS trans_object_id,
        json_extract_string(payload, '$.trans_object_code')                      AS trans_object_code,

        -- Action verb (e.g. 'import', 'export')
        json_extract_string(payload, '$.action')                                 AS action,

        -- Product & variant
        try_cast(json_extract_string(payload, '$.product_id')      AS BIGINT)    AS product_id,
        json_extract_string(payload, '$.product_name')                           AS product_name,
        json_extract_string(payload, '$.product_category')                       AS product_category,
        try_cast(json_extract_string(payload, '$.variant_id')      AS BIGINT)    AS variant_id,
        json_extract_string(payload, '$.variant_name')                           AS variant_name,
        json_extract_string(payload, '$.sku')                                    AS sku,
        json_extract_string(payload, '$.barcode')                                AS barcode,
        json_extract_string(payload, '$.unit')                                   AS unit,

        -- Location
        try_cast(json_extract_string(payload, '$.location_id')     AS BIGINT)    AS location_id,
        json_extract_string(payload, '$.location_label')                         AS location_label,

        -- Inventory movements (quantities)
        try_cast(json_extract_string(payload, '$.import_quantity') AS DOUBLE)    AS import_quantity,
        try_cast(json_extract_string(payload, '$.export_quantity') AS DOUBLE)    AS export_quantity,
        try_cast(json_extract_string(payload, '$.onhand')          AS DOUBLE)    AS onhand,

        -- Stock value movements (MAC-based)
        try_cast(json_extract_string(payload, '$.import_amount')   AS DOUBLE)    AS import_amount,
        try_cast(json_extract_string(payload, '$.export_amount')   AS DOUBLE)    AS export_amount,
        try_cast(json_extract_string(payload, '$.amount')          AS DOUBLE)    AS amount,
        try_cast(json_extract_string(payload, '$.mac')             AS DOUBLE)    AS mac,
        try_cast(json_extract_string(payload, '$.total_mac')       AS DOUBLE)    AS total_mac,

        -- Source channel / system that generated the transaction
        json_extract_string(payload, '$.source')                                 AS source

    FROM deduped
    WHERE rn = 1
)

-- Technical dedup is complete at this point (QUALIFY not needed — entity_id is already unique
-- after ROW_NUMBER PARTITION BY entity_id). Select final flat output; payload discarded.
{% set union_cols = 'entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id, issued_at_utc, log_root_id, log_type, log_type_name, trans_type, trans_type_name, trans_object_id, trans_object_code, action, product_id, product_name, product_category, variant_id, variant_name, sku, barcode, unit, location_id, location_label, import_quantity, export_quantity, onhand, import_amount, export_amount, amount, mac, total_mac, source' %}
SELECT {{ union_cols }} FROM extracted
