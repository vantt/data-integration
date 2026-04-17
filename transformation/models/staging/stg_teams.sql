{{ config(
    materialized='view',
    tags=['staging', 'teams']
) }}

WITH raw_teams AS (
    SELECT * FROM {{ source('sapo_raw', 'teams_raw') }}
),

cleaned AS (
    SELECT
        -- Primary Key
        upper(trim(cast(team_code as string))) as team_code,

        -- Attributes
        trim(cast(team_name as string)) as team_name,
        lower(trim(cast(revenue_type as string))) as revenue_type,
        -- Optional columns: use COALESCE to handle NULL/missing
        coalesce(trim(cast(revenue_filter as string)), '') as revenue_filter,
        coalesce(lower(trim(cast(leader_email as string))), '') as leader_email,
        coalesce(trim(cast(description as string)), '') as description,

        -- Metadata
        cast(ingest_method as string) as ingest_method,
        year,
        month

    FROM raw_teams
    WHERE team_code IS NOT NULL
      AND trim(cast(team_code as string)) != ''
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['team_code']) }} as team_key,
    team_code,
    team_name,
    revenue_type,
    revenue_filter,
    leader_email,
    description,
    ingest_method
FROM cleaned
