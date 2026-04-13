{{ config(
    materialized='incremental',
    unique_key='order_return_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO ORDER RETURNS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields as columns.
--   4. Business dedup by order_return_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same order_return_ids before
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
    FROM {{ source('sapo_raw', 'order_return') }}
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
        json_extract_string(payload, '$.id')                AS order_return_id,
        json_extract_string(payload, '$.modified_on')       AS modified_on,
        json_extract_string(payload, '$.code')              AS return_code,
        json_extract_string(payload, '$.order_id')          AS order_id,
        json_extract_string(payload, '$.order_code')        AS order_code,

        -- Foreign keys
        json_extract_string(payload, '$.customer_id')       AS customer_id,
        json_extract_string(payload, '$.location_id')       AS location_id,
        json_extract_string(payload, '$.account_id')        AS account_id,

        -- Statuses
        json_extract_string(payload, '$.status')            AS return_status,
        json_extract_string(payload, '$.refund_status')     AS refund_status,

        -- Financials
        try_cast(json_extract_string(payload, '$.total_amount')   AS DECIMAL(18,2)) AS total_amount,
        try_cast(json_extract_string(payload, '$.total_quantity') AS INTEGER)        AS total_quantity,

        -- Misc
        json_extract_string(payload, '$.note')              AS note,
        json_extract_string(payload, '$.reason')            AS reason,

        -- Timestamps
        json_extract_string(payload, '$.issued_on')         AS issued_on,
        json_extract_string(payload, '$.received_on')       AS received_on,
        json_extract_string(payload, '$.created_on')        AS created_on

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by order_return_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT order_return_id FROM extracted) new_keys
        ON existing.order_return_id = new_keys.order_return_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_return_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1
