{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    tags=['staging', 'orders']
) }}

-- =================================================================================================
-- HOP 5: STAGING & CLEANING LAYER - SAPO ORDERS
-- =================================================================================================
-- OPTIMIZATION TECHNIQUE: "Strict Late Materialization" & "Double Deduplication"
--
-- 1. MEMORY OPTIMIZATION (OOM Prevention):
--    Instead of `SELECT *` and deduplicating massive JSON blobs (which causes 4MB+ OOM errors in DuckDB),
--    we use a "Late Materialization" strategy:
--      a. Scan 1: Read ONLY lightweight keys (`entity_id`, `timestamp`).
--      b. Dedup 1: Filter to get the "winner" keys using `ROW_NUMBER()`.
--      c. Join: Join "winner" keys back to the source to fetch the heavy `payload`.
--    Crucially, we EXPLICITLY SELECT columns in the join. `SELECT *` in the join can still 
--    trigger memory spill if the optimizer eagerly loads unused columns.
--
-- 2. BUSINESS KEY INTEGRITY (Unique Constraint):
--    Sapo source allows multiple `entity_id`s (technical keys) to share the same `order_id` 
--    (business key). To satisfy the `unique` test on `order_id`, we apply a 
--    Secondary Deduplication step (`final_dedup`) on `order_id` after extraction.
-- =================================================================================================

WITH meta_keys AS (
    -- BƯỚC 1: QUÉT KEY (SCAN KEYS)
    -- Thay vì đọc toàn bộ cột (SELECT *), ta chỉ đọc các cột Key nhẹ để tối ưu bộ nhớ.
    -- Điều này giúp DuckDB lọc dữ liệu rất nhanh mà không tốn RAM cho cột 'payload' nặng.
    SELECT 
        entity_id, 
        event_timestamp, 
        ingest_method
    FROM {{ source('sapo_raw', 'order') }}
    
    {% if is_incremental() %}
    -- LOGIC INCREMENTAL (Tăng trưởng):
    -- Chỉ lấy các bản ghi có thời gian mới hơn lần chạy trước.
    -- Dựa vào MAX(event_timestamp) của chính bảng đích này ({{ this }}).
    WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
    {% endif %}
),

deduped_keys AS (
    -- BƯỚC 2: LỌC TRÙNG KỸ THUẬT (TECHNICAL DEDUPLICATION)
    -- Sapo có thể gửi nhiều event cho cùng 1 entity_id.
    -- Ta dùng Window Function để đánh số thứ tự (rn) ưu tiên bản ghi "xịn" nhất.
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC, -- Ưu tiên mới nhất
                -- Tie-breaker: Nếu cùng giờ, ưu tiên nguồn dữ liệu tin cậy hơn
                CASE
                    WHEN ingest_method = 'webhook' THEN 3     -- Webhook: Realtime chuẩn nhất
                    WHEN ingest_method = 'history_log' THEN 2 -- History: Bổ sung cái thiếu
                    ELSE 1                                    -- Batch: Chạy định kỳ
                END DESC
        ) AS rn
    FROM meta_keys
),

winner_keys AS (
    -- Chỉ giữ lại bản ghi Top 1 (rn = 1)
    SELECT entity_id, event_timestamp, ingest_method
    FROM deduped_keys
    WHERE rn = 1
),

-- BƯỚC 3: LATE MATERIALIZATION (JOIN BACK)
-- Sau khi đã xác định được danh sách Key cần lấy (đã lọc bớt rất nhiều rác),
-- ta mới JOIN ngược lại vào bảng gốc để lấy cột 'payload'.
-- Kỹ thuật này giúp giảm 90% lượng dữ liệu nặng phải di chuyển qua bộ nhớ.
final_source AS (
    SELECT 
        s.entity_id, 
        s.entity_type, 
        s.event_timestamp, 
        s.payload,
        s.ingest_method
    FROM {{ source('sapo_raw', 'order') }} s
    INNER JOIN winner_keys k 
    ON s.entity_id = k.entity_id 
    AND s.event_timestamp = k.event_timestamp
    AND s.ingest_method = k.ingest_method
),

json_parsed AS (
    SELECT 
        entity_id,
        entity_type,
        event_timestamp,
        
        -- =========================================================================================
        -- BƯỚC 4: JSON EXTRACTION & TYPE CASTING
        -- =========================================================================================
        -- Lưu ý cú pháp DuckDB: 
        --   json_extract_string(json_col, '$.path.to.field') -> Trả về TEXT
        --   Sau đó dùng try_cast() để chuyển sang kiểu số/ngày tháng an toàn (tránh lỗi crash).
        
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.code') as order_code,
        json_extract_string(payload, '$.status') as order_status,
        
        -- Mapping logic ...
        json_extract_string(payload, '$.financial_status') as financial_status,
        json_extract_string(payload, '$.fulfillment_status') as fulfillment_status,
        
        -- Logistics (Packed/Received)
        json_extract_string(payload, '$.packed_status') as packed_status,
        json_extract_string(payload, '$.received_status') as received_status,
        
        -- Casting số tiền (DECIMAL)
        try_cast(json_extract_string(payload, '$.total') as DECIMAL(18,2)) as total_amount,
        try_cast(json_extract_string(payload, '$.total_discount') as DECIMAL(18,2)) as total_discount,
        try_cast(json_extract_string(payload, '$.total_tax') as DECIMAL(18,2)) as tax_amount,
        
        -- Keys ngoại
        json_extract_string(payload, '$.customer_id') as customer_id,
        json_extract_string(payload, '$.source_id') as source_id,
        json_extract_string(payload, '$.location_id') as location_id,
        
        -- Staff Info
        json_extract_string(payload, '$.assignee_id') as assignee_id,
        json_extract_string(payload, '$.assignee.name') as assignee_name,
        json_extract_string(payload, '$.assignee.full_name') as assignee_full_name,
        json_extract_string(payload, '$.assignee.email') as assignee_email,
        
        json_extract_string(payload, '$.account_id') as account_id, -- Salesperson
        json_extract_string(payload, '$.account.name') as account_name,
        json_extract_string(payload, '$.account.full_name') as account_full_name,
        json_extract_string(payload, '$.account.email') as account_email,
        json_extract_string(payload, '$.user_name') as user_name,
        
        -- Flattened Customer Info
        json_extract_string(payload, '$.customer_data.name') as customer_name,
        json_extract_string(payload, '$.customer_data.phone_number') as customer_phone,
        json_extract_string(payload, '$.customer_data.email') as customer_email,

        -- Nested Metadata (mảng JSON)
        json_extract_string(payload, '$.billing_address') as billing_address_json,
        json_extract_string(payload, '$.shipping_address') as shipping_address_json,

        -- Extract Detailed Shipping Address
        coalesce(json_extract_string(payload, '$.shipping_address.province'), json_extract_string(payload, '$.shipping_address.city')) as shipping_province,
        json_extract_string(payload, '$.shipping_address.district') as shipping_district,
        json_extract_string(payload, '$.shipping_address.ward') as shipping_ward,
        json_extract_string(payload, '$.shipping_address.address1') as shipping_address1,
        json_extract_string(payload, '$.shipping_address.address2') as shipping_address2,
        json_extract_string(payload, '$.shipping_address.city') as shipping_city,
        json_extract_string(payload, '$.shipping_address.zip') as shipping_zip,
        json_extract_string(payload, '$.shipping_address.country') as shipping_country,
        json_extract_string(payload, '$.shipping_address.phone') as shipping_phone,
        json_extract_string(payload, '$.shipping_address.name') as shipping_name,

        -- Extract Detailed Billing Address
        coalesce(json_extract_string(payload, '$.billing_address.province'), json_extract_string(payload, '$.billing_address.city')) as billing_province,
        json_extract_string(payload, '$.billing_address.district') as billing_district,
        json_extract_string(payload, '$.billing_address.ward') as billing_ward,
        json_extract_string(payload, '$.billing_address.address1') as billing_address1,
        json_extract_string(payload, '$.billing_address.address2') as billing_address2,
        json_extract_string(payload, '$.billing_address.city') as billing_city,
        json_extract_string(payload, '$.billing_address.zip') as billing_zip,
        json_extract_string(payload, '$.billing_address.country') as billing_country,
        json_extract_string(payload, '$.billing_address.company') as billing_company,
        json_extract_string(payload, '$.billing_address.phone') as billing_phone,
        json_extract_string(payload, '$.billing_address.tax_code') as billing_tax_code,
        
        json_extract_string(payload, '$.note') as note,
        json_extract_string(payload, '$.tags') as tags,
        json_extract_string(payload, '$.discount_codes') as discount_codes_json,
        
        json_extract_string(payload, '$.created_on') as created_on,
        json_extract_string(payload, '$.modified_on') as modified_on,
        json_extract_string(payload, '$.issued_on') as issued_on,
        json_extract_string(payload, '$.finalized_on') as finalized_on,
        json_extract_string(payload, '$.cancelled_on') as cancelled_on,
        json_extract_string(payload, '$.completed_on') as completed_on,
        
        -- Kênh bán hàng (Channel)
        json_extract_string(payload, '$.channel') as channel_name,  -- Có thể null
        
        -- Payment Method (Lấy phần tử đầu tiên nếu có)
        json_extract_string(payload, '$.expected_payment_method_id') as payment_method_id,

        payload

    FROM final_source
),

final_dedup AS (
    -- BƯỚC 5: LỌC TRÙNG NGHIỆP VỤ (BUSINESS DEDUPLICATION)
    -- Vì 1 order_id (Business Key) có thể bị sinh ra bởi nhiều entity_id khác nhau trong hệ thống cũ,
    -- nên ta cần lọc 1 lần nữa theo order_id để đảm bảo UNIQUE tuyệt đối cho các bảng facts sau này.
    SELECT *
    FROM json_parsed
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY event_timestamp DESC, modified_on DESC
    ) = 1
)

SELECT
    o.*,
    
    -- =============================================================================================
    -- BƯỚC 6: LÀM GIÀU DỮ LIỆU (DATA ENRICHMENT)
    -- =============================================================================================
    -- Join với các bảng tham chiếu (Seed files) để lấy tên hiển thị thay vì chỉ có ID.
    
    pm.name as payment_method_name,
    s.name as source_name,
    l.name as location_name
    
FROM final_dedup o
LEFT JOIN {{ ref('ref_payment_methods') }} pm ON try_cast(o.payment_method_id as BIGINT) = pm.id
LEFT JOIN {{ ref('ref_order_sources') }} s ON try_cast(o.source_id as BIGINT) = s.id
LEFT JOIN {{ ref('ref_locations') }} l ON try_cast(o.location_id as BIGINT) = l.id
