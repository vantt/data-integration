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
        -- Semantic change 2026-07-10: added 'callback', 'refused', 'purchased'.
        -- A real person answered the phone/replied for all of these — they were
        -- "reached" even if the outcome wasn't a completed conversation.
        -- 'purchased' is a not-yet-shipped contact_outcome enum value (see
        -- plans/reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md);
        -- listed here so this filter is forward-compatible without a follow-up edit.
        -- See schema.yml for the full history note on this column.
        COUNT(*) FILTER (
            WHERE contact_outcome IN (
                'answered', 'replied', 'met', 'callback', 'refused', 'purchased'
            )
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

-- ── Outcome notes: "information collected" leading indicator ──────────────────
-- note_type='outcome' is the default save mode of the M08 Log Activity form
-- (screen_customer_360_activity.py:181/266-275) — reliable, no schema change needed.
outcome_notes AS (
    SELECT
        author_user_id                                                  AS crm_user_id,
        DATE_TRUNC('week',
            created_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*)                                                        AS outcome_notes_count
    FROM {{ ref('stg_crm__note') }}
    WHERE note_type = 'outcome'
      AND author_user_id IS NOT NULL
    GROUP BY 1, 2
),

-- ── New tags: count each (party_id, tag_id) only at its FIRST occurrence ──────
-- (plan.md open question #2) — avoids double-counting a customer being asked
-- about the same health issue / attribute more than once. Credited to whichever
-- staff performed that first tagging.
first_tag_occurrence AS (
    SELECT
        party_id,
        tag_id,
        tagged_by,
        tag_category,
        tagged_at,
        ROW_NUMBER() OVER (
            PARTITION BY party_id, tag_id ORDER BY tagged_at ASC
        )                                                                AS rn
    FROM {{ ref('stg_crm__party_tag') }}
    WHERE tagged_by IS NOT NULL
),
new_tags AS (
    SELECT
        tagged_by                                                       AS crm_user_id,
        DATE_TRUNC('week',
            tagged_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*) FILTER (WHERE tag_category = 'health_concern')        AS health_concern_tags_new,
        -- IS DISTINCT FROM (not !=): tag_category is nullable free-text; a plain
        -- != would silently drop NULL-category tags from both buckets.
        COUNT(*) FILTER (
            WHERE tag_category IS DISTINCT FROM 'health_concern'
        )                                                                AS other_tags_new
    FROM first_tag_occurrence
    WHERE rn = 1
    GROUP BY 1, 2
),

-- ── Channel mix: outreach activities grouped by activity_type ─────────────────
-- Intent was a phone/zalo/sms/other breakdown keyed on channel_type (call|zalo|
-- fb|email|visit|other — crm_activity_log.channel_type, migration 0033). That
-- column is NOT yet exported to the warehouse: crm_activity_log_export's SELECT
-- (orchestration/assets/crm_writeback_assets.py) omits it, same class of gap as
-- the crm_task export gap in plan.md #6. activity_type (call|note|visit|email|
-- chat|other) IS exported and, per the app's hinh_thuc→activity_type mapping
-- (_HT_TO_ACT_TYPE in screen_customer_360_activity.py: call→call, zalo→chat,
-- fb→chat, email→email, visit→visit, other→other), activity_type='call' is an
-- EXACT proxy for channel_type='call' (only hinh_thuc='call' ever produces it).
-- zalo and fb both collapse into 'chat', so this breakdown cannot separate them
-- — that requires exporting channel_type (flagged as an open gap, not fixed here
-- per the CRM staging/export ownership boundary of this phase).
channel_mix AS (
    SELECT
        staff_user_id                                                   AS crm_user_id,
        DATE_TRUNC('week',
            occurred_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        COUNT(*) FILTER (WHERE activity_type = 'call')                 AS activities_call,
        COUNT(*) FILTER (WHERE activity_type = 'chat')                 AS activities_chat,
        COUNT(*) FILTER (WHERE activity_type = 'email')                AS activities_email,
        COUNT(*) FILTER (WHERE activity_type = 'visit')                AS activities_visit,
        COUNT(*) FILTER (WHERE activity_type = 'other')                AS activities_other,
        -- Fallback bucket: legacy/unexpected activity_type values (incl. 'note',
        -- which the enum allows but no current write path produces) and NULL —
        -- never silently dropped (plan.md phase-00 risk note).
        COUNT(*) FILTER (
            WHERE activity_type IS NULL
               OR activity_type NOT IN ('call', 'chat', 'email', 'visit', 'other')
        )                                                                AS activities_unknown
    FROM {{ ref('stg_crm__activity_log') }}
    WHERE staff_user_id IS NOT NULL
    GROUP BY 1, 2
),

-- ── Outcome notes linked back to the exact activity (conversation proxy) ──────
outcome_note_activities AS (
    SELECT DISTINCT source_activity_id
    FROM {{ ref('stg_crm__note') }}
    WHERE note_type = 'outcome'
      AND source_activity_id IS NOT NULL
),

-- ── Call funnel: dial → reach → conversation → wrong number ───────────────────
-- Sprint Gọi Ra 45 ngày (plan.md, bổ sung 2026-07-10).
calls_funnel AS (
    SELECT
        al.staff_user_id                                                AS crm_user_id,
        DATE_TRUNC('week',
            al.occurred_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
        )::DATE                                                         AS week_start_date,
        -- activity_type='call' is an exact proxy for channel_type='call' (see channel_mix note above)
        COUNT(*) FILTER (
            WHERE al.direction = 'out' AND al.activity_type = 'call'
        )                                                                AS calls_dialed,
        -- Real conversation: answered AND (talked >=60s OR an outcome note was
        -- attached to this exact activity). If contact_duration_s is mostly NULL
        -- in practice, this proxy leans on the note fallback (plan.md open Q#6).
        COUNT(*) FILTER (
            WHERE al.contact_outcome = 'answered'
              AND (
                  COALESCE(al.contact_duration_s, 0) >= 60
                  OR ona.source_activity_id IS NOT NULL
              )
        )                                                                AS conversations_count,
        COUNT(*) FILTER (WHERE al.contact_outcome = 'wrong_number')    AS wrong_number_count,
        -- "Zalo connect" (Sprint Gọi Ra KPI, plan.md open Q#7) — capture-as-you-go
        -- contact channel, checked in the disposition strip's T1 phase. Boolean
        -- already derived in staging (stg_crm__activity_log.zalo_connected).
        COUNT(*) FILTER (WHERE al.zalo_connected)                      AS zalo_connected_count
    FROM {{ ref('stg_crm__activity_log') }} al
    LEFT JOIN outcome_note_activities ona
           ON ona.source_activity_id = al.activity_id
    WHERE al.staff_user_id IS NOT NULL
    GROUP BY 1, 2
),

-- ── All (staff, week) combinations present in any source ─────────────────────
spine AS (
    SELECT DISTINCT crm_user_id, week_start_date FROM activities
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM tasks_assigned
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM tasks_completed
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM outcome_notes
    UNION
    SELECT DISTINCT crm_user_id, week_start_date FROM new_tags
    -- channel_mix and calls_funnel are always a subset of activities' (staff, week)
    -- pairs (same source table, same staff_user_id filter) — no need to union them.
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
    COALESCE(os.revenue_vnd, 0)             AS revenue_vnd,

    -- Information-collected KPIs
    COALESCE(onotes.outcome_notes_count, 0)      AS outcome_notes_count,
    COALESCE(nt.health_concern_tags_new, 0)      AS health_concern_tags_new,
    COALESCE(nt.other_tags_new, 0)               AS other_tags_new,

    -- Channel mix (activity_type proxy for channel_type — see channel_mix CTE note)
    COALESCE(cm.activities_call, 0)         AS activities_call,
    COALESCE(cm.activities_chat, 0)         AS activities_chat,
    COALESCE(cm.activities_email, 0)        AS activities_email,
    COALESCE(cm.activities_visit, 0)        AS activities_visit,
    COALESCE(cm.activities_other, 0)        AS activities_other,
    COALESCE(cm.activities_unknown, 0)      AS activities_unknown,

    -- Call funnel KPIs (Sprint Gọi Ra 45 ngày)
    COALESCE(cf.calls_dialed, 0)            AS calls_dialed,
    COALESCE(cf.conversations_count, 0)     AS conversations_count,
    COALESCE(cf.wrong_number_count, 0)      AS wrong_number_count,
    COALESCE(cf.zalo_connected_count, 0)    AS zalo_connected_count

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
LEFT JOIN outcome_notes onotes
       ON onotes.crm_user_id = sp.crm_user_id
      AND onotes.week_start_date = sp.week_start_date
LEFT JOIN new_tags nt
       ON nt.crm_user_id = sp.crm_user_id
      AND nt.week_start_date = sp.week_start_date
LEFT JOIN channel_mix cm
       ON cm.crm_user_id = sp.crm_user_id
      AND cm.week_start_date = sp.week_start_date
LEFT JOIN calls_funnel cf
       ON cf.crm_user_id = sp.crm_user_id
      AND cf.week_start_date = sp.week_start_date

-- Exclude rows where CRM UUID is unknown in dim_staff
-- (these are orphan CRM users not yet matched to Sapo staff)
WHERE s.staff_key IS NOT NULL
