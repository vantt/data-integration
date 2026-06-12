{{ config(
    materialized='view',
    tags=['staging', 'teams']
) }}

WITH raw_members AS (
    SELECT * FROM {{ source('gsheet_raw', 'team_members_raw') }}
),

cleaned AS (
    SELECT
        -- Staff identifier (matches Sapo assignee.email)
        lower(trim(cast(staff_email as string))) as staff_email,

        -- Team FK
        upper(trim(cast(team_code as string))) as team_code,

        -- SCD2 validity period
        try_cast(effective_from as date) as effective_from,
        try_cast(effective_to as date) as effective_to,

        -- Metadata
        cast(ingest_method as string) as ingest_method,
        year,
        month

    FROM raw_members
    WHERE staff_email IS NOT NULL
      AND trim(cast(staff_email as string)) != ''
      AND team_code IS NOT NULL
      AND trim(cast(team_code as string)) != ''
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['staff_email', 'team_code', 'effective_from']) }} as membership_key,
    staff_email,
    team_code,
    effective_from,
    effective_to,

    -- Derived: is this membership currently active?
    (effective_to IS NULL OR effective_to >= current_date) as is_active,

    ingest_method
FROM cleaned
-- Safety net: if multiple partitions are ever read, keep the latest snapshot per SCD2 row
QUALIFY ROW_NUMBER() OVER (PARTITION BY staff_email, team_code, effective_from ORDER BY year DESC, month DESC) = 1
