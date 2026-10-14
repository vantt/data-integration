{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    activity_id,
    party_id,
    TRY_CAST(customer_id AS INTEGER)            AS customer_id,
    activity_type,
    direction,
    channel,
    -- channel_type (migration 0033): call|zalo|fb|email|visit|other — a coarser,
    -- reliable enum vs. activity_type (which folds zalo/fb both into 'chat').
    -- Gap fix (coordinator 260710, phase-01 addendum): was exported nowhere before —
    -- the outreach-effort funnel needs it to split zalo/fb, not just "chat".
    channel_type,
    outcome,
    contact_outcome,
    outcome_reason,
    callback_at::TIMESTAMPTZ                    AS callback_at,
    contact_duration_s::INTEGER                 AS contact_duration_s,
    task_id,
    related_order_code,
    staff_user_id,
    occurred_at::TIMESTAMPTZ                    AS occurred_at,
    created_at::TIMESTAMPTZ                     AS logged_at,
    -- custom_fields is a JSON string (crm_activity_log.custom_fields, migration 0030).
    -- zalo_connected (plan 260709-1638, sprint gọi ra 260710) — "đã kết bạn Zalo"
    -- checkbox captured via Log Activity; defaults false when the key is absent
    -- (older rows, or channel_type not call/zalo where the checkbox isn't shown).
    COALESCE(
        TRY_CAST(json_extract_string(custom_fields, '$.zalo_connected') AS BOOLEAN),
        false
    )                                            AS zalo_connected
FROM {{ source('crm_export', 'crm_activity_log') }}
WHERE TRY_CAST(customer_id AS INTEGER) IS NOT NULL
