{{ config(materialized='view', tags=['mart', 'crm']) }}
-- mart_crm_activity_log: canonical CRM activity mart
-- outcome_reason: pilot enum — review after 2-week NV field trial before locking (design §8.3).
-- is_reached: true when contact was successfully connected (answered / replied / met).
SELECT
    activity_id,
    party_id,
    customer_id,
    activity_type,
    direction,
    channel,
    contact_outcome,
    outcome_reason,
    CASE WHEN contact_outcome IN ('answered', 'replied', 'met')
         THEN true ELSE false END                AS is_reached,
    callback_at,
    contact_duration_s,
    task_id,
    related_order_code,
    staff_user_id,
    occurred_at,
    logged_at                                    AS created_at
FROM {{ ref('stg_crm__activity_log') }}
