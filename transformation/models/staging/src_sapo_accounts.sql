{{ config(
    materialized='incremental',
    unique_key='account_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo', 'accounts']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO ACCOUNTS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, ingest_method priority).
--   3. Extract ALL scalar JSON fields from payload.
--   4. Business dedup by account_id (latest event_timestamp wins).
--   5. Discard payload -> frees memory for downstream models.
-- =================================================================================================

WITH raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        payload
    FROM {{ source('sapo_raw', 'account') }}
    {% if is_incremental() %}
    WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
    {% endif %}
),

deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
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

-- Step 2: Business dedup by account_id -- operates on flat data only, no payload
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY account_id
    ORDER BY event_timestamp DESC, try_cast(modified_on AS TIMESTAMP) DESC NULLS LAST
) = 1
