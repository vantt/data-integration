{{ config(
    materialized='incremental',
    unique_key='sapo_customer_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO CUSTOMERS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, ingest_method priority).
--   3. Extract ALL scalar JSON fields from payload.
--   4. Business dedup by sapo_customer_id (latest event_timestamp wins).
--   5. Discard payload -> frees memory for downstream models.
-- =================================================================================================

WITH raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        payload
    FROM {{ source('sapo_raw', 'customer') }}
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

        -- Customer IDs
        json_extract_string(payload, '$.id') as sapo_customer_id,
        json_extract_string(payload, '$.modified_on') as modified_on,
        json_extract_string(payload, '$.code') as customer_code,

        -- Personal info
        json_extract_string(payload, '$.name') as full_name,
        json_extract_string(payload, '$.phone_number') as phone_number,
        json_extract_string(payload, '$.email') as email,
        json_extract_string(payload, '$.status') as status,

        -- Date of birth
        json_extract_string(payload, '$.birthday') as birthday,
        json_extract_string(payload, '$.dob') as dob,

        -- Gender (consolidate sex/gender)
        coalesce(json_extract_string(payload, '$.sex'), json_extract_string(payload, '$.gender')) as sex,

        -- Group
        json_extract_string(payload, '$.customer_group') as customer_group,

        -- Address
        json_extract_string(payload, '$.addresses[0].city') as city,
        coalesce(json_extract_string(payload, '$.addresses[0].province'), json_extract_string(payload, '$.addresses[0].city')) as province,
        json_extract_string(payload, '$.addresses[0].district') as district,
        json_extract_string(payload, '$.addresses[0].ward') as ward,
        json_extract_string(payload, '$.addresses[0].address1') as address1,
        json_extract_string(payload, '$.addresses[0].country') as country,

        -- Financials
        try_cast(json_extract_string(payload, '$.total_expense') as DECIMAL(18,2)) as total_expense,
        try_cast(json_extract_string(payload, '$.order_count') as INTEGER) as orders_count,
        try_cast(json_extract_string(payload, '$.loyalty_point') as INTEGER) as loyalty_point,
        try_cast(json_extract_string(payload, '$.debt') as DECIMAL(18,2)) as debt,

        -- Timestamps
        json_extract_string(payload, '$.created_on') as created_on

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by sapo_customer_id -- operates on flat data only, no payload
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY sapo_customer_id
    ORDER BY event_timestamp DESC, modified_on DESC
) = 1
