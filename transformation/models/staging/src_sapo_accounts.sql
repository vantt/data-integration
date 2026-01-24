{{ config(
    materialized='view',
    tags=['source', 'sapo', 'accounts']
) }}

-- =================================================================================================
-- HOP 4: VIRTUAL STAGING VIEW - ACCOUNTS
-- =================================================================================================
-- Purpose: Deduplicate and version control Sapo Accounts data.
-- =================================================================================================

WITH raw_data AS (
    SELECT 
        *,
        strptime(year || '-' || month || '-01', '%Y-%m-%d') as partition_date
    FROM {{ source('sapo_raw', 'account') }}
),

deduplicated AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id 
            ORDER BY event_timestamp DESC
        ) as rn
    FROM raw_data
)

SELECT * EXCLUDE (rn)
FROM deduplicated
WHERE rn = 1
