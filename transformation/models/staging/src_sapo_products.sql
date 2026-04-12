{{ config(
    materialized='incremental',
    unique_key='product_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo', 'products']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO PRODUCTS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, ingest_method priority).
--   3. Extract scalar JSON fields + nested arrays as text for downstream unnest.
--   4. Business dedup by product_id (latest event_timestamp + modified_on wins).
--   5. Discard payload -> frees memory for downstream models.
-- =================================================================================================

WITH raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        payload
    FROM {{ source('sapo_raw', 'product') }}
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

-- Tech dedup + JSON extraction (payload discarded after this CTE)
extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,

        -- Product IDs
        json_extract_string(payload, '$.id') as product_id,
        json_extract_string(payload, '$.tenant_id') as tenant_id,
        json_extract_string(payload, '$.modified_on') as modified_on,

        -- Product info
        json_extract_string(payload, '$.name') as product_name,
        json_extract_string(payload, '$.status') as product_status,
        json_extract_string(payload, '$.product_type') as product_type,
        json_extract_string(payload, '$.description') as description,

        -- Brand
        json_extract_string(payload, '$.brand_id') as brand_id,
        json_extract_string(payload, '$.brand') as brand,

        -- Category
        json_extract_string(payload, '$.category_id') as category_id,
        json_extract_string(payload, '$.category') as category,
        json_extract_string(payload, '$.category_code') as category_code,

        -- Options
        json_extract_string(payload, '$.opt1') as opt1,
        json_extract_string(payload, '$.opt2') as opt2,
        json_extract_string(payload, '$.opt3') as opt3,

        -- Flags
        json_extract_string(payload, '$.medicine') as medicine,
        json_extract_string(payload, '$.tags') as tags,

        -- Images
        json_extract_string(payload, '$.image_path') as image_path,
        json_extract_string(payload, '$.image_name') as image_name,

        -- Timestamps
        json_extract_string(payload, '$.created_on') as created_on,

        -- Nested JSON arrays (as text for downstream unnest models)
        json_extract_string(payload, '$.variants') as variants_json,
        json_extract_string(payload, '$.options') as options_json,
        json_extract_string(payload, '$.images') as images_json

    FROM deduped
    WHERE rn = 1
)

-- Business dedup by product_id
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY product_id
    ORDER BY event_timestamp DESC, try_cast(modified_on AS TIMESTAMP) DESC NULLS LAST
) = 1
