{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    tags=['staging', 'customers']
) }}

-- =================================================================================================
-- HOP 5: STAGING & CLEANING LAYER
-- =================================================================================================
-- Mục đích:
-- 1. Chuẩn hóa thông tin khách hàng từ JSON.
-- 2. Định dạng lại số điện thoại, email, ngày sinh (nếu cần).
-- 3. Xử lý Incremental & Deduplication từ Raw Source.
-- =================================================================================================

WITH raw_data AS (
    SELECT 
        *,
        -- DuckDB hive_partitioning=1 columns
        ingest_method,
        year,
        month
    FROM {{ source('sapo_raw', 'customer') }}

    {% if is_incremental() %}
    -- LOGIC INCREMENTAL (Tăng trưởng): 
    -- 1. Chỉ lấy dữ liệu mới hơn dữ liệu đã có trong bảng đích ({{ this }})
    -- 2. Dựa trên cột 'event_timestamp' (thời gian sự kiện xảy ra trên nguồn)
    WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
    {% endif %}
),

deduped AS (
    -- BƯỚC 2: DE-DUPLICATION (LỌC TRÙNG)
    -- Mục tiêu: Lấy bản ghi "chất lượng nhất" cho mỗi khách hàng (entity_id).
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC, -- Ưu tiên bản ghi mới nhất
                -- Tie-breaker (Quy tắc phụ): Ưu tiên nguồn tin cậy hơn
                CASE
                    WHEN ingest_method = 'webhook' THEN 3     -- Realtime (tin cậy nhất)
                    WHEN ingest_method = 'history_log' THEN 2 -- Lịch sử (bổ sung)
                    ELSE 1                                    -- Batch (quét định kỳ)
                END DESC
        ) AS rn
    FROM raw_data
),

final_source AS (
    -- Chỉ giữ lại bản ghi số 1
    SELECT * EXCLUDE (rn)
    FROM deduped
    WHERE rn = 1
)

SELECT 
    entity_id,
    entity_type,
    event_timestamp,
    
    -- =========================================================================================
    -- JSON EXTRACTION (TRÍCH XUẤT DỮ LIỆU)
    -- =========================================================================================
    -- json_extract_string: Trả về chuỗi raw text từ JSON.
    -- coalesce: Lấy giá trị đầu tiên không null (dùng để fallback).
    
    json_extract_string(payload, '$.id') as sapo_customer_id,
    json_extract_string(payload, '$.code') as customer_code,
    json_extract_string(payload, '$.name') as full_name,
    json_extract_string(payload, '$.phone_number') as phone_number,
    json_extract_string(payload, '$.email') as email,
    json_extract_string(payload, '$.status') as status,
    
    json_extract_string(payload, '$.birthday') as birthday,
    json_extract_string(payload, '$.gender') as gender,
    
    -- Address (Taking the default array item if available, or just addresses[0])
    json_extract_string(payload, '$.addresses[0].city') as city,
    coalesce(json_extract_string(payload, '$.addresses[0].province'), json_extract_string(payload, '$.addresses[0].city')) as province,
    json_extract_string(payload, '$.addresses[0].district') as district,
    json_extract_string(payload, '$.addresses[0].ward') as ward,
    json_extract_string(payload, '$.addresses[0].address1') as address1,
    json_extract_string(payload, '$.addresses[0].country') as country,
    
    -- Financials
    try_cast(json_extract_string(payload, '$.total_expense') as DECIMAL(18,2)) as total_spent,
    try_cast(json_extract_string(payload, '$.order_count') as INTEGER) as orders_count,
    try_cast(json_extract_string(payload, '$.debt') as DECIMAL(18,2)) as debt,
    
    json_extract_string(payload, '$.created_on') as created_on,
    json_extract_string(payload, '$.modified_on') as modified_on,
    
    payload

FROM final_source
