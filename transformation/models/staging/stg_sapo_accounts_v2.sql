{{ config(
    materialized='view',
    tags=['staging', 'accounts']
) }}

-- =================================================================================================
-- STAGING: SAPO ACCOUNTS
-- =================================================================================================
-- Purpose:
--   Reads from src_sapo_accounts (already extracted & deduped).
--   Clean and flatten account data for usage in Dimensions.
--   No JSON extraction needed — data is already flat from src_.
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_accounts_v2') }}
)

SELECT
    entity_id,
    account_id,

    -- Names (coalesce for best available name)
    coalesce(full_name, user_name, last_name || ' ' || first_name, 'Unknown Staff') as staff_name,
    email as staff_email,
    mobile as staff_phone,

    status,
    tenant_id,

    -- Timestamps
    try_cast(created_on as TIMESTAMPTZ) as created_at,
    try_cast(modified_on as TIMESTAMPTZ) as updated_at,
    event_timestamp,
    ingest_method

FROM source_data
