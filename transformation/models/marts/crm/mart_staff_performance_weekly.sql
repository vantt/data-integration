{{ config(
    tags=['mart', 'crm', 'staff'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Cross-system staff performance: CRM activities + tasks + Sapo orders.
-- Grain: staff × ISO week (Monday ICT).
-- Identity bridge: dim_staff.crm_user_id links CRM UUIDs to Sapo staff_key.

WITH staff AS (
    SELECT staff_key, staff_id, crm_user_id, full_name, email
    FROM {{ ref('dim_staff') }}
    WHERE staff_id != '-1'
),

-- ── CRM activities ────────────────────────────────────────────────────────────
activities AS (
    SELECT
        staff_user_id                                                   AS crm_user_id,
        DATE_TRUNC('week',
            occurred_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*)                                                        AS activities_total,
        COUNT(*) FILTER (WHERE direction = 'out')                      AS activities_outbound,
        COUNT(*) FILTER (
            WHERE contact_outcome IN ('answered', 'replied', 'met')
        )                                                               AS contacts_reached,
        COALESCE(SUM(contact_duration_s), 0)                           AS call_duration_s
    FROM {{ ref('stg_crm__activity_log') }}
    WHERE staff_user_id IS NOT NULL
    GROUP BY 1, 2
),

-- ── CRM tasks assigned (by week task was created) ─────────────────────────────
tasks_assigned AS (
    SELECT
        assignee_user_id                                                AS crm_user_id,
        DATE_TRUNC('week',
            created_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*)                                                        AS tasks_assigned
    FROM {{ ref('stg_crm__task') }}
    WHERE assignee_user_id IS NOT NULL
    GROUP BY 1, 2
),

-- ── CRM tasks completed (by week completed) ───────────────────────────────────
tasks_completed AS (
    SELECT
        assignee_user_id                                                AS crm_user_id,
        DATE_TRUNC('week',
            completed_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*)                                                        AS tasks_completed
    FROM {{ ref('stg_crm__task') }}
    WHERE assignee_user_id IS NOT NULL
      AND completed_at IS NOT NULL
    GROUP BY 1, 2
),

-- ── Sapo orders sold (seller attribution, confirmed orders only) ──────────────
orders_sold AS (
    SELECT
        fo.seller_staff_key,
        -- date_key is INTEGER YYYYMMDD in ICT; already timezone-correct
        DATE_TRUNC('week', strptime(CAST(fo.date_key AS VARCHAR), '%Y%m%d')::DATE
        )::DATE                                                         AS week_start_date,
        COUNT(*)                                                        AS orders_sold,
        COALESCE(SUM(fo.net_revenue), 0)                               AS revenue_vnd
    FROM {{ ref('fact_orders') }} fo
    WHERE fo.is_active_order = TRUE
    GROUP BY 1, 2
),

-- ── All (staff, week) combinations present in any source ─────────────────────
spine AS (
    SELECT DISTINCT crm_user_id, week_start_date FROM activities
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM tasks_assigned
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM tasks_completed
    -- Orders are joined via staff_key, added in final select
)

SELECT
    s.staff_key,
    s.staff_id,
    s.crm_user_id,
    s.full_name,
    sp.week_start_date,

    -- Activity KPIs
    COALESCE(a.activities_total, 0)         AS activities_total,
    COALESCE(a.activities_outbound, 0)      AS activities_outbound,
    COALESCE(a.contacts_reached, 0)         AS contacts_reached,
    COALESCE(a.call_duration_s, 0)          AS call_duration_s,
    CASE WHEN a.activities_outbound > 0
         THEN ROUND(
             a.contacts_reached * 100.0 / a.activities_outbound, 1
         ) END                              AS reach_rate_pct,

    -- Task KPIs
    COALESCE(ta.tasks_assigned, 0)          AS tasks_assigned,
    COALESCE(tc.tasks_completed, 0)         AS tasks_completed,

    -- Sales KPIs
    COALESCE(os.orders_sold, 0)             AS orders_sold,
    COALESCE(os.revenue_vnd, 0)             AS revenue_vnd

FROM spine sp
-- Resolve CRM UUID → dim_staff
LEFT JOIN staff s ON s.crm_user_id = sp.crm_user_id
LEFT JOIN activities a
       ON a.crm_user_id = sp.crm_user_id
      AND a.week_start_date = sp.week_start_date
LEFT JOIN tasks_assigned ta
       ON ta.crm_user_id = sp.crm_user_id
      AND ta.week_start_date = sp.week_start_date
LEFT JOIN tasks_completed tc
       ON tc.crm_user_id = sp.crm_user_id
      AND tc.week_start_date = sp.week_start_date
-- Orders join via staff_key (Sapo-side identity)
LEFT JOIN orders_sold os
       ON os.seller_staff_key = s.staff_key
      AND os.week_start_date = sp.week_start_date

-- Exclude rows where CRM UUID is unknown in dim_staff
-- (these are orphan CRM users not yet matched to Sapo staff)
WHERE s.staff_key IS NOT NULL
