{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    user_id                                     AS crm_user_id,
    staff_id::INTEGER                           AS staff_id,
    lower(trim(email))                          AS email,
    full_name::VARCHAR                          AS full_name,
    role::VARCHAR                               AS crm_role,
    is_active::BOOLEAN                          AS is_active,
    lark_user_id::VARCHAR                       AS lark_user_id,
    created_at::TIMESTAMPTZ                     AS created_at,
    updated_at::TIMESTAMPTZ                     AS updated_at
FROM {{ source('crm_export', 'crm_app_user') }}
WHERE user_id IS NOT NULL
