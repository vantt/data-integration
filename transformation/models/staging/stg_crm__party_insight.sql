{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    insight_id,
    party_id,
    customer_id::INTEGER                         AS customer_id,
    insight_type,
    body,
    confidence,
    source_note_id,
    created_by,
    updated_at::TIMESTAMPTZ                      AS updated_at,
    created_at::TIMESTAMPTZ                      AS created_at
FROM {{ source('crm_export', 'crm_party_insight') }}
WHERE deleted_at IS NULL
