{{ config(
    materialized='view',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- HOP 4: VIRTUAL STAGING VIEW
-- =================================================================================================
-- Mục đích:
-- 1. Đọc dữ liệu Raw từ Data Lake (file Parquet) do dlt pipeline sinh ra.
-- 2. Thực hiện Deduplication (loại bỏ trùng lặp) để đảm bảo mỗi Entity ID chỉ có 1 dòng duy nhất.
-- 3. Đóng vai trò là "Virtual Sorted Log": Luôn trả về trạng thái mới nhất của đơn hàng.
-- =================================================================================================

WITH raw_data AS (
    -- Bước 1: Đọc toàn bộ file Parquet từ Data Lake
    -- Nguồn: defined in models/sources.yml (trỏ tới data_lake/sapo_raw/orders)
    SELECT 
        *,
        -- Tạo partition date ảo nếu cần dùng để lọc (DuckDB tự động nhận partition từ đường dẫn thư mục)
        strptime(year || '-' || month || '-01', '%Y-%m-%d') as partition_date
    FROM {{ source('sapo_raw', 'order') }}
),

deduplicated AS (
    -- Bước 2: Đánh số thứ tự phiên bản (Versioning)
    SELECT 
        *,
        -- LOGIC DEDUPLICATION:
        -- Chúng ta gom nhóm theo ID thực thể (entity_id).
        -- Sắp xếp theo thời gian sự kiện (event_timestamp) giảm dần.
        -- -> Dòng đầu tiên (rn=1) chính là trạng thái mới nhất của đơn hàng này.
        ROW_NUMBER() OVER (
            PARTITION BY entity_id 
            ORDER BY event_timestamp DESC
        ) as rn
    FROM raw_data
)

-- Bước 3: Chỉ lấy bản ghi mới nhất (rn=1) và loại bỏ cột số thứ tự
SELECT * EXCLUDE (rn)
FROM deduplicated
WHERE rn = 1
