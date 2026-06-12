{{ config(
    materialized='incremental',
    unique_key='purchase_order_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO PURCHASE ORDERS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields + nested arrays/objects as text columns.
--   4. Business dedup by purchase_order_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same purchase_order_ids before
--     final dedup, so a later load never overwrites a more-recent record.
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
    FROM {{ source('sapo_v2_raw', 'purchase_order') }}
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
                try_cast(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ) DESC NULLS LAST,
                CASE
                    WHEN ingest_method = 'webhook' THEN 3
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
),

-- Step 1: Tech dedup + JSON extraction (payload discarded after this CTE)
extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,

        -- IDs & codes
        json_extract_string(payload, '$.id')            AS purchase_order_id,
        json_extract_string(payload, '$.modified_on')   AS modified_on,
        json_extract_string(payload, '$.code')          AS purchase_order_code,

        -- Status & foreign keys
        json_extract_string(payload, '$.status')        AS po_status,
        json_extract_string(payload, '$.supplier_id')   AS supplier_id,
        json_extract_string(payload, '$.location_id')   AS location_id,
        json_extract_string(payload, '$.account_id')    AS account_id,

        -- Misc
        json_extract_string(payload, '$.note')          AS note,
        json_extract_string(payload, '$.tags')          AS tags,

        -- Timestamps
        json_extract_string(payload, '$.created_on')    AS created_on,

        -- Nested JSON arrays/objects (as text for downstream models)
        json_extract_string(payload, '$.line_items')    AS line_items_json,
        json_extract_string(payload, '$.supplier_data') AS supplier_data_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by purchase_order_id — compare new vs existing before overwriting
-- NOTE: Use explicit column names (not SELECT *) to prevent positional mismatch
{% set union_cols = 'entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id, purchase_order_id, modified_on, purchase_order_code, po_status, supplier_id, location_id, account_id, note, tags, created_on, line_items_json, supplier_data_json' %}
SELECT * FROM (
    SELECT {{ union_cols }} FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT {{ union_cols }} FROM {{ this }}
    WHERE purchase_order_id IN (SELECT DISTINCT purchase_order_id FROM extracted)
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY purchase_order_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1
