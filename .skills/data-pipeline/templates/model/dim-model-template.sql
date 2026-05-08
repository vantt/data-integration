{{ config(
    tags=['mart', 'dim', '{SOURCE}'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- DIMENSION: DIM_{ENTITY_UPPER}
-- =============================================================================
-- CRITICAL: location="{{ get_rolling_location() }}" là BẮT BUỘC cho mart models
--           (nếu thiếu, generate_serving_db.py báo "Empty folder" và drop view)
--
-- Pattern:
--   1. Surrogate key qua dbt_utils.generate_surrogate_key
--   2. UNION ALL một row "Unknown" để fact rows không bị drop khi missing FK
--   3. Đọc từ std_{ENTITY} (golden layer) — không đọc src_/stg_ trực tiếp
-- =============================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('std_{entity}') }}
),

-- Main dimension rows
dimension AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['{entity}_id']) }}  AS {entity}_key,
        {entity}_id,

        -- Natural attributes
        name                    AS {entity}_name,
        status                  AS status,
        -- TODO: thêm các attributes cần cho BI

        -- Timestamps
        created_at,
        updated_at

    FROM source_data
),

-- Unknown row — cho fact rows có FK null/invalid, dùng COALESCE fact-side
unknown_row AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}  AS {entity}_key,
        'Unknown'   AS {entity}_id,
        'Unknown'   AS {entity}_name,
        'UNKNOWN'   AS status,
        NULL        AS created_at,
        NULL        AS updated_at
)

SELECT * FROM dimension
UNION ALL
SELECT * FROM unknown_row
