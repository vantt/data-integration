{{ config(
    materialized='view',
    tags=['staging', 'customers', 'contacts']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMER CONTACTS
-- =================================================================================================
-- Purpose:
--   Unnest $.contacts (object array) from stg_sapo_v2_customers.
--   B2B contact persons (name/phone/email/position) attached to a customer account.
--   One row per (sapo_customer_id, contact_id).
-- =================================================================================================

WITH source AS (
    SELECT sapo_customer_id, contacts_json
    FROM {{ ref('stg_sapo_v2_customers') }}
    WHERE contacts_json IS NOT NULL
      AND contacts_json NOT IN ('', '[]', 'null')
),

unnested AS (
    SELECT
        sapo_customer_id,
        unnest(from_json(contacts_json, '["JSON"]')) AS item_json
    FROM source
)

SELECT
    sapo_customer_id,
    json_extract_string(item_json, '$.id')           AS contact_id,
    json_extract_string(item_json, '$.name')         AS contact_name,
    json_extract_string(item_json, '$.phone')        AS phone,
    json_extract_string(item_json, '$.email')        AS email,
    json_extract_string(item_json, '$.position')     AS position,
    json_extract_string(item_json, '$.organization') AS organization
FROM unnested
WHERE item_json IS NOT NULL
