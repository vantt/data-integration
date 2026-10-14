{{ config(
    tags=['mart', 'crm', 'staff'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: CRM OUTREACH EFFORT BY ACTION_TYPE, WEEKLY  ("Bảng A")
-- =============================================================================
-- Plan: plans/260709-1638-crm-outreach-effort-report (Track B, phase 3).
-- Grain: (staff_key, week_start_date, action_type) — rolls up
-- int_crm_outreach_effort_events (task_id x action_type) to staff x week x
-- action_type for Metabase/BI.
--
-- This is Bảng A ONLY (effort-by-action_type). The phase-03 file's "Bảng B"
-- (info-collected: outcome notes / new tags, NOT split by action_type) is
-- deliberately NOT built here — that concept already ships in
-- mart_staff_performance_weekly (phase 0, same day), and duplicating it under
-- a different grain here would create two sources of truth for the same
-- number. See phase-03-outreach-effort-weekly-mart.md "Output shape" section
-- and its final "Quyết định implement" line.
--
-- int_crm_outreach_effort_events.staff_user_id is the task assignee (correct,
-- fixed post-implementation — was briefly wired from the linked activity's
-- staff instead, which was NULL for most rows). Only created_at/completed_at
-- still need a direct stg_crm__task join here since the intermediate model
-- only exposes the derived week_start_date, not the raw timestamps
-- avg_days_to_complete needs. Scoped to the same source filter as the
-- intermediate model so the task_id population matches exactly.
-- =============================================================================

WITH events AS (
    SELECT *
    FROM {{ ref('int_crm_outreach_effort_events') }}
),

task_detail AS (
    SELECT task_id, created_at, completed_at
    FROM {{ ref('stg_crm__task') }}
    WHERE source = 'action_queue_claim'
),

staff AS (
    SELECT staff_key, crm_user_id
    FROM {{ ref('dim_staff') }}
    WHERE staff_id != '-1'
)

SELECT
    s.staff_key,
    e.week_start_date,
    e.action_type,

    -- Task KPIs — COUNT(DISTINCT task_id): the `events` grain is already
    -- (task_id, action_type), and this GROUP BY includes action_type, so a
    -- task_id appears at most once per group (enforced by phase-02's
    -- unique_combination_of_columns(task_id, action_type) test). DISTINCT is
    -- a defensive guard here, not a fix for an actual duplicate.
    -- 'cancelled' status (present in real data, not in the open/doing/done
    -- set the phase-03 spec text names) intentionally counts toward NEITHER
    -- bucket — it's neither still-pending nor completed.
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.status IN ('open', 'doing')) AS tasks_claimed_pending,
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.status = 'done')            AS tasks_completed,

    -- Avg calendar days created_at -> completed_at, done tasks only.
    ROUND(
        AVG(DATE_DIFF('day', td.created_at, td.completed_at))
            FILTER (WHERE e.status = 'done' AND td.completed_at IS NOT NULL),
        1
    )                                                                       AS avg_days_to_complete,

    -- Effort/reach KPIs — phase-03 double-count-trap decision: a task's
    -- effort is counted PER action_type row it bundled, not split/divided
    -- across them (1 call serving 2 action_types counts once toward each,
    -- not 0.5 each — see phase-03 file's "Cạm bẫy double-count" section).
    COUNT(DISTINCT e.task_id)                             AS contacts_attempted,
    COUNT(DISTINCT e.task_id) FILTER (WHERE e.is_reached)  AS contacts_reached,
    ROUND(
        COUNT(DISTINCT e.task_id) FILTER (WHERE e.is_reached) * 100.0
            / NULLIF(COUNT(DISTINCT e.task_id), 0),
        1
    )                                                                       AS reach_rate_pct

FROM events e
JOIN task_detail td ON td.task_id = e.task_id
JOIN staff s        ON s.crm_user_id = e.staff_user_id
GROUP BY 1, 2, 3
