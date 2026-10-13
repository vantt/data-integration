{{ config(
    materialized='view',
    tags=['standard', 'teams']
) }}

-- Standard team membership (SCD2): thin pass-through over stg_team_members.
-- Grain: 1/(staff_email, team_code, effective_from).
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_team_members') }}
)

SELECT
    membership_key,
    staff_email,
    team_code,
    effective_from,
    effective_to,
    is_active,
    ingest_method,
    'gsheet' AS source_system
FROM source_data
