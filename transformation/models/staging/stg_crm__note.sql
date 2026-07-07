{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    note_id,
    party_id,
    customer_id::INTEGER                         AS customer_id,
    note_type,
    body,
    author_user_id,
    pinned::INTEGER                              AS pinned,
    pinned_until::TIMESTAMPTZ                    AS pinned_until,
    visibility,
    task_id,
    campaign_id,
    source_activity_id,
    updated_at::TIMESTAMPTZ                      AS updated_at,
    updated_by_user_id,
    created_at::TIMESTAMPTZ                      AS created_at
FROM {{ source('crm_export', 'crm_note') }}
WHERE deleted_at IS NULL
