{{ config(
    materialized='table',
    tags=['mart', 'intermediate', 'crm']
) }}

-- =============================================================================
-- INTERMEDIATE: CRM OUTREACH EFFORT EVENTS
-- =============================================================================
-- Plan: plans/260709-1638-crm-outreach-effort-report (Track B, phase 2).
-- Grain: (task_id, action_type) — one row per claimed task, exploded per
-- action_type it bundled at claim time. A claim with N claimed_action_types
-- produces N rows (the same call/effort "counts" for every action_type it was
-- claimed for). A task with no claimed_action_types (NULL — pre-cutover data,
-- since claimed_action_types is a fix-forward-only snapshot column added in
-- phase 01) produces exactly 1 row with action_type = NULL.
--
-- Not a mart. Just the join + explode layer so phase 03's weekly mart can
-- GROUP BY (staff, week, action_type) without repeating this logic, and so
-- this layer can be tested in isolation for uniqueness/explode correctness.
--
-- Scope only tasks sourced from action_queue_claim, per phase-02 spec — other
-- task sources (manual, verify_account, action_queue) never carry
-- claimed_action_types and aren't part of the action-type-attributed effort
-- story this model exists to serve.
--
-- Deliberately NOT filtering any action-queue eligibility flag here (e.g.
-- is_us_gift_recipient) — this is an effort/activity-log layer, not an
-- eligibility layer. A customer excluded from the action queue can still have
-- a real activity log entry from a rep calling outside that flow; dropping it
-- here would silently lose real effort data. Filter at phase 03 if a report
-- needs it.
--
-- staff_user_id is left as the raw CRM UUID (assignee_user_id at claim time)
-- — joining to dim_staff.staff_key to get a real name is phase 03's job
-- (intermediate models stay close to source; marts denormalize).
-- =============================================================================

WITH task AS (
    SELECT
        task_id, party_id, customer_id, assignee_user_id,
        created_at, completed_at, status, channel AS task_channel,
        claimed_action_types
    FROM {{ ref('stg_crm__task') }}
    WHERE source = 'action_queue_claim'
),

-- ── Explode claimed_action_types JSON array ──────────────────────────────────
-- claimed_action_types is a JSON array string, e.g. '["REORDER_PREEMPT","PROGRESS_CHECK"]'.
-- Same LATERAL UNNEST(json_extract(..., '$[*]')) pattern already used elsewhere
-- in this project (see int_order_tags.sql, stg_sapo_v2_customer_tags.sql) —
-- verified working against the duckdb 1.5.4 engine this dbt project runs on.
-- UNION ALL with the NULL/empty branch below (rather than a plain LEFT JOIN
-- LATERAL) because UNNEST of an empty/NULL array yields zero rows, not one
-- NULL row — and the spec requires exactly 1 row (action_type = NULL) for
-- tasks with no claimed_action_types.
task_actions AS (
    SELECT DISTINCT
        t.task_id,
        TRIM(REPLACE(a.action_type_raw::VARCHAR, '"', '')) AS action_type
    FROM task t,
    LATERAL UNNEST(
        json_extract(t.claimed_action_types, '$[*]')
    ) AS a(action_type_raw)
    WHERE t.claimed_action_types IS NOT NULL
      AND t.claimed_action_types NOT IN ('', '[]')

    UNION ALL

    SELECT DISTINCT
        t.task_id,
        NULL AS action_type
    FROM task t
    WHERE t.claimed_action_types IS NULL
       OR t.claimed_action_types IN ('', '[]')
),

task_exploded AS (
    SELECT
        t.task_id, t.party_id, t.customer_id, t.assignee_user_id,
        t.created_at, t.completed_at, t.status, t.task_channel,
        ta.action_type
    FROM task t
    JOIN task_actions ta ON ta.task_id = t.task_id
),

-- ── Activity log linked to the task ──────────────────────────────────────────
-- A task can have MORE THAN ONE activity logged against it in practice (e.g. a
-- no_answer attempt followed by a later redial within the same claimed task —
-- confirmed against real data: one task_id currently has 5 linked activities).
-- Grain here stays (task_id, action_type), so multiple activities per task
-- must collapse to one representative row per task for the single-valued
-- columns (contact_outcome, staff_user_id, channel) — most recent occurred_at
-- wins (the final known result of that outreach effort). Info-collected
-- columns (outcome_note_count, *_tags_new) are summed across ALL activities
-- of the task instead (see task_effort_info CTE below) since those represent
-- everything collected during the whole task, not just its last call attempt.
activity AS (
    SELECT
        activity_id, task_id, contact_outcome, occurred_at, staff_user_id,
        channel_type
    FROM {{ ref('stg_crm__activity_log') }}
    WHERE task_id IS NOT NULL
),

activity_primary AS (
    SELECT activity_id, task_id, contact_outcome, occurred_at, staff_user_id, channel_type
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY task_id ORDER BY occurred_at DESC, activity_id DESC
            ) AS rn
        FROM activity
    )
    WHERE rn = 1
),

-- ── Outcome notes: "information collected" during the call ──────────────────
-- note_type='outcome' linked back to the exact activity via source_activity_id
-- (stg_crm__note already filters deleted_at IS NULL upstream — no need to
-- repeat it here).
outcome_note AS (
    SELECT source_activity_id, COUNT(*) AS outcome_note_count
    FROM {{ ref('stg_crm__note') }}
    WHERE note_type = 'outcome'
      AND source_activity_id IS NOT NULL
    GROUP BY 1
),

-- ── New tags: count each (party_id, tag_id) only at its FIRST-EVER occurrence ─
-- (same rule as mart_staff_performance_weekly's first_tag_occurrence CTE —
-- plan.md open question #2) linked back to the activity via source_activity_id
-- where that attach happened (migration 0044, phase 01). Currently always 0 in
-- practice: source_activity_id has no real data yet (phase-01 report,
-- "Handoff wiring" — the UI wiring to pass activity_id into the tag-attach
-- call is not done). Logic is forward-correct for when that wiring lands.
new_tag AS (
    SELECT
        source_activity_id,
        COUNT(*) FILTER (WHERE tag_category = 'health_concern')            AS health_concern_tags_new,
        COUNT(*) FILTER (WHERE tag_category IS DISTINCT FROM 'health_concern') AS other_tags_new
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY party_id, tag_id ORDER BY tagged_at) AS rn
        FROM {{ ref('stg_crm__party_tag') }}
    )
    WHERE rn = 1
      AND source_activity_id IS NOT NULL
    GROUP BY 1
),

-- ── Broadcast info-collected metrics to the WHOLE task ───────────────────────
-- Open decision in phase-02 file: apply health_concern_tags_new (and, by the
-- same reasoning, outcome_note_count / other_tags_new) to EVERY action_type
-- row of a task, not just one representative row — the information was
-- gathered by that call/task as a whole, not attributable to one action_type
-- over another. Summed across all activities linked to the task (see activity
-- CTE note on multi-activity tasks).
task_effort_info AS (
    SELECT
        act.task_id,
        COALESCE(SUM(onote.outcome_note_count), 0)        AS outcome_note_count,
        COALESCE(SUM(nt.health_concern_tags_new), 0)       AS health_concern_tags_new,
        COALESCE(SUM(nt.other_tags_new), 0)                AS other_tags_new
    FROM activity act
    LEFT JOIN outcome_note onote ON onote.source_activity_id = act.activity_id
    LEFT JOIN new_tag nt         ON nt.source_activity_id    = act.activity_id
    GROUP BY act.task_id
)

SELECT
    te.task_id,
    te.party_id,
    dc.customer_key,
    te.action_type,
    te.status,
    te.assignee_user_id                                                 AS staff_user_id,
    -- week_start_date: completed_at if the task has one, else created_at (per spec).
    DATE_TRUNC(
        'week',
        COALESCE(te.completed_at, te.created_at) AT TIME ZONE 'Asia/Ho_Chi_Minh'
    )::DATE                                                             AS week_start_date,
    -- channel_type (call|zalo|fb|email|visit|other, migration 0033) is the
    -- reliable "kind of contact" enum — crm_activity_log.channel is a raw
    -- value (phone number / zalo handle), NOT a channel type (confirmed,
    -- phase-00 implementation report). channel_type was not staged when the
    -- phase-02 spec text was drafted; it is now (phase-01 addendum), so this
    -- deliberately uses it instead of the literal "channel" the phase file's
    -- pseudocode named — falls back to the task's own channel (crm_task.channel,
    -- the queued action's intended channel) when there's no linked activity yet.
    COALESCE(ap.channel_type, te.task_channel)                          AS channel,
    ap.contact_outcome,
    -- Harmonized with mart_staff_performance_weekly's contacts_reached
    -- (Phase 0, same day) rather than the phase-02 spec's literal narrower
    -- list — same "reached" concept must mean the same enum set everywhere
    -- reach_rate_pct is computed, or Track A/Track B numbers silently diverge.
    ap.contact_outcome IN (
        'answered', 'replied', 'met', 'callback', 'refused', 'purchased'
    )                                                                    AS is_reached,
    COALESCE(tei.outcome_note_count, 0)                                 AS outcome_note_count,
    COALESCE(tei.health_concern_tags_new, 0)                            AS health_concern_tags_new,
    COALESCE(tei.other_tags_new, 0)                                     AS other_tags_new
FROM task_exploded te
LEFT JOIN activity_primary ap    ON ap.task_id = te.task_id
LEFT JOIN task_effort_info tei   ON tei.task_id = te.task_id
-- party_id -> Sapo customer_key bridge: customer_id is already resolved from
-- party_id via crm_party_identity(identity_type='sapo_customer') at export
-- time (orchestration/assets/crm_writeback_assets.py::_dedup_identity_join) —
-- every crm_export table already carries a resolved Sapo customer_id column,
-- so re-deriving it here from party_id would duplicate that join for no
-- reason. Same pattern as mart_crm_activity_log.sql / int_crm_party_tag_flags.sql.
LEFT JOIN {{ ref('dim_customers') }} dc
       ON TRY_CAST(dc.customer_id AS BIGINT) = TRY_CAST(te.customer_id AS BIGINT)
