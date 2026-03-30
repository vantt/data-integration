{{ config(
    materialized='view',
    tags=['standard', 'accounts']
) }}

-- =================================================================================================
-- STANDARD ACCOUNTS (STAFF)
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_accounts') }}
)

SELECT
    -- Identity
    account_id,
    'sapo' as source_system,

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
