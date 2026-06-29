{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    activity_id,
    party_id,
    TRY_CAST(customer_id AS INTEGER)            AS customer_id,
    activity_type,
    direction,
    channel,
    outcome,
    contact_outcome,
    callback_at::TIMESTAMPTZ                    AS callback_at,
    contact_duration_s::INTEGER                 AS contact_duration_s,
    task_id,
    related_order_code,
    staff_user_id,
    occurred_at::TIMESTAMPTZ                    AS occurred_at,
    created_at::TIMESTAMPTZ                     AS logged_at
FROM {{ source('crm_export', 'crm_activity_log') }}
WHERE TRY_CAST(customer_id AS INTEGER) IS NOT NULL
