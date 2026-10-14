{{ config(
    tags=['mart', 'crm', 'customer'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Contact outcome funnel: who was called, when, result — linked to warehouse customers.
-- Grain: one row per CRM activity log entry.

SELECT
    a.activity_id,
    a.customer_id,
    c.customer_key,
    c.full_name,
    c.phone,
    c.value_group,
    a.activity_type,
    a.direction,
    a.channel,
    a.outcome,
    a.contact_outcome,
    a.outcome_reason,
    a.occurred_at,
    a.logged_at,
    a.staff_user_id,
    a.task_id,
    a.related_order_code,
    a.contact_duration_s,
    -- Derived
    a.contact_outcome IN ('answered', 'replied', 'met')    AS is_reached,
    CASE a.contact_outcome
        WHEN 'answered' THEN 'Reached'
        WHEN 'no_answer' THEN 'No answer'
        WHEN 'callback'  THEN 'Callback'
        WHEN 'refused'   THEN 'Refused'
        ELSE 'Unknown'
    END                                                     AS outcome_label,
    DATE_TRUNC('day', a.occurred_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE AS activity_date

FROM {{ ref('stg_crm__activity_log') }} a
LEFT JOIN {{ ref('dim_customers') }} c ON TRY_CAST(c.customer_id AS BIGINT) = TRY_CAST(a.customer_id AS BIGINT)
