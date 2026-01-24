{{ config(
    materialized='view',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- HOP 4: VIRTUAL STAGING VIEW
-- =================================================================================================
-- Mục đích:
-- 1. Cung cấp dữ liệu Khách hàng sạch từ Data Lake.
-- 2. Loại bỏ các bản ghi trùng lặp do cơ chế "Append-only" của dlt (ghi đè lịch sử).
-- =================================================================================================

WITH raw_data AS (
    -- Bước 1: Đọc từ source 'sapo_raw.customers' (xem models/sources.yml)
    SELECT *
    FROM {{ source('sapo_raw', 'customers') }}
),

deduplicated AS (
    -- Bước 2: Lấy bản ghi mới nhất dựa trên event_timestamp
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id 
            ORDER BY event_timestamp DESC
        ) as rn
    FROM raw_data
)

-- Bước 3: Filter lấy bản mới nhất
SELECT * EXCLUDE (rn)
FROM deduplicated
WHERE rn = 1
