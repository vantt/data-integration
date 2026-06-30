{{ config(
    materialized='view',
    tags=['staging', 'customers', 'tags']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMER TAGS
-- =================================================================================================
-- Purpose:
--   Unnest $.tags (string array) from stg_sapo_v2_customers.
--   One row per (sapo_customer_id, tag_name).
-- Syntax: LATERAL UNNEST(json_extract(..., '$[*]')) — see int_order_tags.sql for reference.
-- =================================================================================================

WITH source AS (
    SELECT sapo_customer_id, tags_json
    FROM {{ ref('stg_sapo_v2_customers') }}
    WHERE tags_json IS NOT NULL
      AND tags_json NOT IN ('', '[]', 'null')
)

SELECT
    sapo_customer_id,
    TRIM(REPLACE(t.tag_name::VARCHAR, '"', '')) AS tag_name
FROM source,
LATERAL UNNEST(
    json_extract(tags_json, '$[*]')
) AS t(tag_name)
