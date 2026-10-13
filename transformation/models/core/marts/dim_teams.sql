{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH teams AS (
    SELECT * FROM {{ ref('stg_teams') }}
),

team_members AS (
    SELECT * FROM {{ ref('stg_team_members') }}
),

-- Count active members per team
member_counts AS (
    SELECT
        team_code,
        COUNT(*) as active_member_count
    FROM team_members
    WHERE is_active = true
    GROUP BY team_code
)

SELECT
    t.team_key,
    t.team_code,
    t.team_name,
    t.revenue_type,
    t.revenue_filter,
    t.leader_email,
    t.description,
    COALESCE(mc.active_member_count, 0) as active_member_count,
    true as is_active

FROM teams t
LEFT JOIN member_counts mc ON t.team_code = mc.team_code

UNION ALL

-- Unknown Member
SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as team_key,
    'UNK' as team_code,
    'Unknown Team' as team_name,
    'member' as revenue_type,
    '' as revenue_filter,
    '' as leader_email,
    '' as description,
    0 as active_member_count,
    true as is_active
