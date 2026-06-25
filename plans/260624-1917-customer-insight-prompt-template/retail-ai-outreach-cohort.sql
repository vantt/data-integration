-- Retail AI-outreach cohort
-- Chọn khách RETAIL đáng để sinh kịch bản tiếp cận bằng AI:
--   - dữ liệu đáng tin (loại B2B/đại lý rò rỉ, loại margin âm/hỏng)
--   - đủ quan hệ để cá nhân hóa (có chu kỳ + sản phẩm neo)
--   - còn cứu được (không quá ngủ đông) + đáng công (giá trị hoặc đang trong cửa sổ mua)
--
-- run_priority: xếp hàng đợi Ở TẦNG SQL (KHÔNG đưa vào prompt AI — prompt v1 đã bỏ priority_score).
-- Các ngưỡng (recency<=270, order_count>=2...) là tham số kinh doanh, chỉnh theo chu kỳ ngành hàng.
--
-- Nguồn: serving view canonical. Chạy trong Metabase/pipeline dùng nguyên `main_marts.dim_customers`.
-- Chạy ad-hoc trên host Windows: thay FROM bằng
--   read_parquet('app_data/data_lake/export/marts/rolling/dim_customers/*.parquet')

WITH base AS (
    SELECT *
    FROM main_marts.dim_customers
    WHERE customer_type = 'RETAIL'
)
SELECT
    customer_id,
    full_name,
    phone,
    geo_region,
    value_group,
    lifetime_value,
    order_count,
    lifecycle_stage,
    recency_days,
    avg_days_between_orders,
    next_purchase_signal,
    discount_sensitivity,
    top_affinity_product,
    ROUND(avg_order_contribution_margin_pct, 3) AS margin_pct,

    -- Thứ tự gọi: giá trị + tín hiệu mua + độ tươi + sức khỏe biên.
    -- DUE_SOON ưu tiên hơn OVERDUE (bắt trước khi rớt, dễ thắng hơn).
    (
        CASE value_group
            WHEN 'VALUE_VIP'    THEN 40
            WHEN 'VALUE_GOLD'   THEN 30
            WHEN 'VALUE_SILVER' THEN 15
            ELSE 5
        END
      + CASE next_purchase_signal
            WHEN 'DUE_SOON' THEN 30
            WHEN 'OVERDUE'  THEN 15
            ELSE 0
        END
      + CASE
            WHEN recency_days <= 120 THEN 20
            WHEN recency_days <= 180 THEN 10
            ELSE 0
        END
      + CAST(COALESCE(avg_order_contribution_margin_pct, 0) * 10 AS INTEGER)
    ) AS run_priority

FROM base
WHERE
    -- ── Liên hệ được ──
    is_contactable = TRUE
    AND contact_quality <> 'masked'

    -- ── Tin dữ liệu: loại đại lý gán nhầm RETAIL ──
    AND COALESCE(acquisition_source, '') <> 'Đại Lý'

    -- ── Hợp lý kinh tế: loại khách lỗ biên / margin hỏng (vd sàn/reseller như "Leflair") ──
    AND is_margin_negative = FALSE
    AND COALESCE(avg_order_contribution_margin_pct, 0) > 0

    -- ── Đủ quan hệ: cần chu kỳ + sản phẩm để neo kịch bản ──
    AND order_count >= 2
    AND top_affinity_sku IS NOT NULL

    -- ── Còn cứu được: bỏ khách ngủ đông quá sâu (khó thắng, contact dễ chết) ──
    AND recency_days <= 270

    -- ── Đáng công: hoặc giá trị cao, hoặc đang trong cửa sổ mua ──
    AND (
        value_group IN ('VALUE_VIP', 'VALUE_GOLD')
        OR next_purchase_signal IN ('DUE_SOON', 'OVERDUE')
    )

    -- ── (Tùy chọn) Loại tên giống tổ chức/sàn — bật nếu cần, dễ loại nhầm người thật ──
    -- AND lower(full_name) NOT SIMILAR TO '%(shop|store|mart|cty|công ty|c\.ty|tnhh|leflair|sàn)%'

ORDER BY run_priority DESC, lifetime_value DESC;
