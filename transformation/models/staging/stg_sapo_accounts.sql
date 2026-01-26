{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    tags=['staging', 'accounts']
) }}

-- =================================================================================================
-- HOP 5: STAGING LAYER - SAPO ACCOUNTS
-- =================================================================================================
-- Purpose: Clean and flatten account data for usage in Dimensions.
-- =================================================================================================

WITH raw_data AS (
    SELECT 
        *,
        ingest_method
    FROM {{ source('sapo_raw', 'account') }}
    
    {% if is_incremental() %}
    -- LOGIC INCREMENTAL: 
    -- 1. Chỉ lấy delta (dữ liệu mới) dựa trên 'event_timestamp'
    WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
    {% endif %}
),

deduped AS (
    -- BƯỚC 2: DE-DUPLICATION
    -- Lọc trùng theo entity_id (Technical Key)
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
                -- Ưu tiên Webhook > History > Batch để đảm bảo tính Realtime
                CASE
                    WHEN ingest_method = 'webhook' THEN 3
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
),

final_source AS (
    SELECT * EXCLUDE (rn)
    FROM deduped
    WHERE rn = 1
),

json_parsed AS (
    SELECT 
        entity_id,
        event_timestamp,
        ingest_method,
        
        -- =========================================================================================
        -- TRÍCH XUẤT THÔNG TIN TÀI KHOẢN (ACCOUNT INFO)
        -- =========================================================================================
        -- Cấu trúc: Entity này đại diện cho nhân viên bán hàng (Salesperson)
        
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
        
    FROM final_source
)

SELECT
    entity_id,
    account_id,
    
    -- Names
    coalesce(full_name, user_name, last_name || ' ' || first_name, 'Unknown Staff') as staff_name,
    email as staff_email,
    mobile as staff_phone,
    
    status,
    tenant_id,
    
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(modified_on as TIMESTAMP) as updated_at,
    event_timestamp,
    ingest_method
    
FROM json_parsed
