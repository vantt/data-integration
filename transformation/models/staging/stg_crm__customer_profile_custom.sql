{{ config(materialized='view', tags=['staging', 'crm']) }}

-- Raw JSON + static extract from 4 seeded field_keys (crm_custom_field_def).
-- When adding new field_key to crm_custom_field_def, add json_extract_string here.
SELECT
    party_id,
    custom                                              AS custom_json,
    updated_at::TIMESTAMPTZ                             AS updated_at,
    json_extract_string(custom, '$.skin_type')          AS skin_type,
    json_extract_string(custom, '$.loyal_tier')         AS loyal_tier,
    json_extract_string(custom, '$.preferred_contact')  AS preferred_contact,
    json_extract_string(custom, '$.note_internal')      AS note_internal
FROM {{ source('crm_export', 'crm_customer_profile_custom') }}
