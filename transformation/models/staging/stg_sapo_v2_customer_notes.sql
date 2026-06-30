{{ config(
    materialized='view',
    tags=['staging', 'customers', 'notes']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMER NOTES
-- =================================================================================================
-- Purpose:
--   Unnest $.notes (object array) from stg_sapo_v2_customers.
--   One row per (sapo_customer_id, note_id).
-- Syntax: unnest(from_json(..., '["JSON"]')) — see stg_sapo_v2_order_items.sql for reference.
-- =================================================================================================

WITH source AS (
    SELECT sapo_customer_id, notes_json
    FROM {{ ref('stg_sapo_v2_customers') }}
    WHERE notes_json IS NOT NULL
      AND notes_json NOT IN ('', '[]', 'null')
),

unnested AS (
    SELECT
        sapo_customer_id,
        unnest(from_json(notes_json, '["JSON"]')) AS item_json
    FROM source
)

SELECT
    sapo_customer_id,
    json_extract_string(item_json, '$.id')         AS note_id,
    json_extract_string(item_json, '$.content')    AS content,
    json_extract_string(item_json, '$.created_on') AS created_on,
    json_extract_string(item_json, '$.account_id') AS account_id
FROM unnested
WHERE item_json IS NOT NULL
