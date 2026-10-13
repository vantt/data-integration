{{ config(
    materialized='view',
    tags=['standard', 'teams']
) }}

-- Standard sales teams: thin pass-through over stg_teams.
-- Grain: 1/team_code.
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_teams') }}
)

SELECT
    team_key,
    team_code,
    team_name,
    revenue_type,
    revenue_filter,
    leader_email,
    description,
    ingest_method,
    'gsheet' AS source_system
FROM source_data
