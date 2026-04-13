{{ config(
    materialized='incremental',
    unique_key='stock_adjustment_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO STOCK ADJUSTMENTS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields + nested arrays as text columns.
--   4. Business dedup by stock_adjustment_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same stock_adjustment_ids before
--     final dedup, so a later load never overwrites a more-recent record.
-- =================================================================================================

WITH
{% if is_incremental() %}
_cursor AS (
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
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
    FROM {{ source('sapo_raw', 'stock_adjustment') }}
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
        json_extract_string(payload, '$.id')            AS stock_adjustment_id,
        json_extract_string(payload, '$.modified_on')   AS modified_on,
        json_extract_string(payload, '$.code')          AS adjustment_code,

        -- Status & foreign keys
        json_extract_string(payload, '$.status')        AS adjustment_status,
        json_extract_string(payload, '$.location_id')   AS location_id,
        json_extract_string(payload, '$.account_id')    AS account_id,

        -- Misc
        json_extract_string(payload, '$.reason')        AS reason,
        json_extract_string(payload, '$.note')          AS note,

        -- Financials
        try_cast(json_extract_string(payload, '$.total') AS DECIMAL(18,2)) AS total,

        -- Timestamps
        json_extract_string(payload, '$.adjusted_on')   AS adjusted_on,
        json_extract_string(payload, '$.created_on')    AS created_on,

        -- Nested JSON arrays (as text for downstream models)
        json_extract_string(payload, '$.line_items')    AS line_items_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by stock_adjustment_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT stock_adjustment_id FROM extracted) new_keys
        ON existing.stock_adjustment_id = new_keys.stock_adjustment_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY stock_adjustment_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1
