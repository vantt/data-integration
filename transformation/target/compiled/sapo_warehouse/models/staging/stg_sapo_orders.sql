

-- =================================================================================================
-- HOP 5: STAGING & CLEANING LAYER - SAPO ORDERS
-- =================================================================================================
-- Purpose:
-- 1. Extract raw JSON fields from `src_sapo_orders` into typed columns.
-- 2. Handle Sapo-specific JSON paths (e.g. `customer_data`, `fulfillments` array structure).
-- 3. Prepare data for the Standardized Layer (`std_orders`).
--
-- Source System: Sapo (Vietnam E-commerce Platform)
--
-- Key Transformations:
-- - JSON Extraction: using `json_extract_string` (DuckDB compatible).
-- - Type Casting: `try_cast` to DECIMAL/INTEGER/TIMESTAMP to prevent pipeline failures on bad data.
-- - Flattening: Extracting nested objects like `billing_address` for easier access.
-- =================================================================================================

WITH raw_source AS (
    -- Bước 1: Đọc từ Hop 4 (đã deduplicate)
    SELECT * FROM "data_integration2"."main_staging"."src_sapo_orders"
),

json_parsed AS (
    SELECT 
        entity_id,
        entity_type,
        event_timestamp,
        
        -- =========================================================================================
        -- JSON EXTRACTION & TYPE CASTING
        -- =========================================================================================
        -- Lưu ý cú pháp DuckDB: 
        --   json_extract_string(json_col, '$.path.to.field') -> Trả về TEXT
        --   Sau đó dùng try_cast() để chuyển sang kiểu số/ngày tháng an toàn (tránh lỗi crash).
        
        -- Default extraction (Postgres -> DuckDB transition)
        -- Postgres: payload->>'field'
        -- DuckDB: json_extract_string(payload, '$.field')
        
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.code') as order_code,
        json_extract_string(payload, '$.status') as order_status,
        json_extract_string(payload, '$.created_on') as created_on,
        json_extract_string(payload, '$.modified_on') as modified_on,
        json_extract_string(payload, '$.channel') as channel_name, -- Extracted channel name
        json_extract_string(payload, '$.issued_on') as issued_on,
        json_extract_string(payload, '$.finalized_on') as finalized_on,
        json_extract_string(payload, '$.completed_on') as completed_on,
        json_extract_string(payload, '$.cancelled_on') as cancelled_on,
        
        json_extract_string(payload, '$.financial_status') as financial_status,
        json_extract_string(payload, '$.fulfillment_status') as fulfillment_status,
        
        -- Addresses
        json_extract_string(payload, '$.billing_address') as billing_address_json,
        json_extract_string(payload, '$.shipping_address') as shipping_address_json,
        json_extract_string(payload, '$.fulfillment_status') as fulfillment_status,
        json_extract_string(payload, '$.note') as note,
        json_extract_string(payload, '$.tags') as tags,
        json_extract_string(payload, '$.discount_codes') as discount_codes_json,
        
        -- Financials
        try_cast(json_extract_string(payload, '$.total') as DECIMAL(18,2)) as total_amount,
        try_cast(json_extract_string(payload, '$.total_discount') as DECIMAL(18,2)) as total_discount,
        try_cast(json_extract_string(payload, '$.total_tax') as DECIMAL(18,2)) as tax_amount,
        
        -- FKs
        json_extract_string(payload, '$.customer_id') as customer_id,
        json_extract_string(payload, '$.assignee_id') as assignee_id,
        json_extract_string(payload, '$.account_id') as account_id, -- Salesperson
        json_extract_string(payload, '$.expected_payment_method_id') as payment_method_id,
        json_extract_string(payload, '$.source_id') as source_id,
        json_extract_string(payload, '$.location_id') as location_id,
        
        -- Flattened Customer Info (from payload, not join)
        json_extract_string(payload, '$.customer_data.name') as customer_name,
        json_extract_string(payload, '$.customer_data.phone_number') as customer_phone,
        json_extract_string(payload, '$.customer_data.email') as customer_email,

        payload

    FROM raw_source
)

SELECT
    o.*,
    
    -- =============================================================================================
    -- DATA ENRICHMENT (LOOKUP)
    -- =============================================================================================
    -- Thay vì chỉ hiển thị ID (vô nghĩa với người dùng), ta hiển thị Tên.
    -- Sử dụng LEFT JOIN để không làm mất đơn hàng nếu thiếu thông tin tham chiếu.
    
    pm.name as payment_method_name,
    s.name as source_name,
    l.name as location_name

FROM json_parsed o
LEFT JOIN "data_integration2"."main"."ref_payment_methods" pm ON try_cast(o.payment_method_id as BIGINT) = pm.id
LEFT JOIN "data_integration2"."main"."ref_order_sources" s ON try_cast(o.source_id as BIGINT) = s.id
LEFT JOIN "data_integration2"."main"."ref_locations" l ON try_cast(o.location_id as BIGINT) = l.id