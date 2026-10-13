{{ config(
    materialized='view',
    tags=['staging', 'customers', 'addresses']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMER ADDRESSES
-- =================================================================================================
-- Purpose:
--   Unnest $.addresses (object array) from stg_sapo_v2_customers.
--   Captures ALL address slots (index 0+); addresses[0] scalars in dim_customers_base
--   are the primary address; this bridge table holds the full set per customer.
--   One row per (sapo_customer_id, address_id).
-- =================================================================================================

WITH source AS (
    SELECT sapo_customer_id, addresses_json
    FROM {{ ref('stg_sapo_v2_customers') }}
    WHERE addresses_json IS NOT NULL
      AND addresses_json NOT IN ('', '[]', 'null')
),

unnested AS (
    SELECT
        sapo_customer_id,
        unnest(from_json(addresses_json, '["JSON"]')) AS item_json
    FROM source
)

SELECT
    sapo_customer_id,
    json_extract_string(item_json, '$.id')           AS address_id,
    json_extract_string(item_json, '$.address1')     AS address1,
    json_extract_string(item_json, '$.address2')     AS address2,
    json_extract_string(item_json, '$.ward')         AS ward,
    json_extract_string(item_json, '$.district')     AS district,
    json_extract_string(item_json, '$.city')         AS city,
    json_extract_string(item_json, '$.province')     AS province,
    json_extract_string(item_json, '$.zip')          AS zip,
    json_extract_string(item_json, '$.country')      AS country,
    json_extract_string(item_json, '$.phone')        AS phone,
    json_extract_string(item_json, '$.company')      AS company,
    json_extract_string(item_json, '$.first_name')   AS first_name,
    json_extract_string(item_json, '$.last_name')    AS last_name
FROM unnested
WHERE item_json IS NOT NULL
