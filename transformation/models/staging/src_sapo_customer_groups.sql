{{ config(
    materialized='incremental',
    unique_key='customer_group_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    enabled=false,
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO CUSTOMER GROUPS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields as columns.
--   4. Business dedup by customer_group_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same customer_group_ids before
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
    FROM {{ source('sapo_raw', 'customer_group') }}
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
        json_extract_string(payload, '$.id')                AS customer_group_id,
        json_extract_string(payload, '$.modified_on')       AS modified_on,
        json_extract_string(payload, '$.code')              AS group_code,
        json_extract_string(payload, '$.name')              AS group_name,

        -- Status & type
        json_extract_string(payload, '$.status')            AS group_status,
        json_extract_string(payload, '$.group_type')        AS group_type,
        json_extract_string(payload, '$.condition_type')    AS condition_type,

        -- Flags & counts
        json_extract_string(payload, '$.is_default')        AS is_default,
        try_cast(json_extract_string(payload, '$.count_customer') AS INTEGER) AS customer_count,

        -- Misc
        json_extract_string(payload, '$.note')              AS note,

        -- Timestamps
        json_extract_string(payload, '$.created_on')        AS created_on

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by customer_group_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT customer_group_id FROM extracted) new_keys
        ON existing.customer_group_id = new_keys.customer_group_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY customer_group_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1
