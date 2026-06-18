{{ config(
    materialized='view',
    tags=['standard', 'accounts']
) }}

-- =================================================================================================
-- STANDARD ACCOUNTS (STAFF)
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_accounts') }}
)

SELECT
    -- Identity
    account_id,
    'sapo_v2' as source_system,
    'v2'   as source_version,

    -- Staff info
    staff_name,
    staff_email,
    staff_phone,
    status,
    tenant_id,

    -- Timestamps
    created_at,
    updated_at

FROM source_data
