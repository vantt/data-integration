{{ config(
    materialized='view',
    tags=['staging', 'accounts']
) }}

-- =================================================================================================
-- HOP 5: STAGING LAYER - SAPO ACCOUNTS
-- =================================================================================================
-- Purpose: Clean and flatten account data for usage in Dimensions.
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM {{ ref('src_sapo_accounts') }}
),

json_parsed AS (
    SELECT 
        entity_id,
        event_timestamp,
        
        -- Extraction
        json_extract_string(payload, '$.id') as account_id,
        json_extract_string(payload, '$.full_name') as full_name,
        json_extract_string(payload, '$.email') as email,
        json_extract_string(payload, '$.user_name') as user_name,
        json_extract_string(payload, '$.first_name') as first_name,
        json_extract_string(payload, '$.last_name') as last_name,
        
        json_extract_string(payload, '$.mobile') as mobile,
        json_extract_string(payload, '$.status') as status,
        json_extract_string(payload, '$.tenant_id') as tenant_id,
        
        json_extract_string(payload, '$.created_on') as created_on,
        json_extract_string(payload, '$.modified_on') as modified_on
        
    FROM raw_source
)

SELECT
    account_id,
    
    -- Names
    coalesce(full_name, user_name, last_name || ' ' || first_name, 'Unknown Staff') as staff_name,
    email as staff_email,
    mobile as staff_phone,
    
    status,
    tenant_id,
    
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(modified_on as TIMESTAMP) as updated_at
    
FROM json_parsed
