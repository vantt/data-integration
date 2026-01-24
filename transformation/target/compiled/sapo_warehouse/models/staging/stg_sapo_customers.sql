

-- =================================================================================================
-- HOP 5: STAGING & CLEANING LAYER
-- =================================================================================================
-- Mục đích:
-- 1. Chuẩn hóa thông tin khách hàng từ JSON.
-- 2. Định dạng lại số điện thoại, email, ngày sinh (nếu cần).
-- =================================================================================================

WITH raw_source AS (
    -- Đọc từ Hop 4
    SELECT * FROM "data_integration2"."main_staging"."src_sapo_customers"
)

SELECT 
    entity_id,
    entity_type,
    event_timestamp,
    
    -- =========================================================================================
    -- JSON EXTRACTION
    -- =========================================================================================
    
    json_extract_string(payload, '$.id') as sapo_customer_id,
    json_extract_string(payload, '$.code') as customer_code,
    json_extract_string(payload, '$.name') as full_name,
    json_extract_string(payload, '$.phone_number') as phone_number,
    json_extract_string(payload, '$.email') as email,
    json_extract_string(payload, '$.status') as status,
    
    json_extract_string(payload, '$.birthday') as birthday,
    json_extract_string(payload, '$.gender') as gender,
    
    -- Financials
    try_cast(json_extract_string(payload, '$.total_expense') as DECIMAL(18,2)) as total_spent,
    try_cast(json_extract_string(payload, '$.order_count') as INTEGER) as orders_count, -- Check if this field exists or needs calculation
    try_cast(json_extract_string(payload, '$.debt') as DECIMAL(18,2)) as debt,
    
    json_extract_string(payload, '$.created_on') as created_on,
    json_extract_string(payload, '$.modified_on') as modified_on,
    
    payload

FROM raw_source