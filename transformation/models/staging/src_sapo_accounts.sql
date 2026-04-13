{{ config(
    materialized='incremental',
    unique_key='account_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo', 'accounts']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO ACCOUNTS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields from payload.
--   4. Business dedup by account_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload -> frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same account_ids before
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
    FROM {{ source('sapo_raw', 'account') }}
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

        -- Account IDs
        json_extract_string(payload, '$.id') as account_id,
        json_extract_string(payload, '$.modified_on') as modified_on,

        -- Account info
        json_extract_string(payload, '$.full_name') as full_name,
        json_extract_string(payload, '$.email') as email,
        json_extract_string(payload, '$.user_name') as user_name,
        json_extract_string(payload, '$.first_name') as first_name,
        json_extract_string(payload, '$.last_name') as last_name,
        json_extract_string(payload, '$.mobile') as mobile,
        json_extract_string(payload, '$.status') as status,
        json_extract_string(payload, '$.tenant_id') as tenant_id,

        -- Timestamps
        json_extract_string(payload, '$.created_on') as created_on

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by account_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT account_id FROM extracted) new_keys
        ON existing.account_id = new_keys.account_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1
