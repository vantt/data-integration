{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    party_id,
    customer_id::INTEGER                        AS customer_id,
    last_contacted_at::TIMESTAMPTZ              AS last_contacted_at,
    last_contact_result,
    last_contact_channel,
    updated_at::TIMESTAMPTZ                     AS updated_at
FROM {{ source('crm_export', 'crm_last_contact') }}
WHERE customer_id IS NOT NULL
