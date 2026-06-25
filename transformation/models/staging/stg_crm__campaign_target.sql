{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    campaign_id,
    party_id,
    customer_id::INTEGER                        AS customer_id,
    status,
    assigned_user_id,
    last_touch_at::TIMESTAMPTZ                  AS last_touch_at,
    converted_order_code,
    converted_revenue_vnd::BIGINT               AS converted_revenue_vnd,
    converted_at::TIMESTAMPTZ                   AS converted_at,
    status = 'converted'                        AS is_converted
FROM {{ source('crm_export', 'crm_campaign_target') }}
WHERE customer_id IS NOT NULL
