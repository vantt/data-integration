{{ config(
    materialized='view',
    tags=['monitoring', 'tags']
) }}

-- =============================================================================
-- MONITORING: UNCATEGORIZED TAGS
-- =============================================================================
-- Purpose: Surface new/unknown tags for review and categorization
-- Action: Add pattern to seeds/ref_tag_categories.csv when new tags appear
-- Docs: transformation/docs/TAG_HANDLING.md
-- =============================================================================

WITH uncategorized AS (
    SELECT
        tag_value,
        COUNT(DISTINCT order_id) as order_count,
        MIN(order_id) as sample_order_id
    FROM {{ ref('int_order_tags') }}
    WHERE tag_category = 'uncategorized'
    GROUP BY 1
)

SELECT
    tag_value,
    order_count,
    sample_order_id,
    CASE
        WHEN tag_value LIKE 'Shopee_%' THEN 'suggest: channel_storefront (Shopee)'
        WHEN tag_value LIKE 'Lazada_%' THEN 'suggest: channel_storefront (Lazada)'
        WHEN tag_value LIKE 'Tiki_%' THEN 'suggest: channel_storefront (Tiki)'
        WHEN tag_value LIKE 'Ad_id_%' THEN 'suggest: marketing_ad'
        WHEN tag_value LIKE 'Post_ID%' THEN 'suggest: marketing_post'
        WHEN tag_value LIKE 'ID Khách hàng%' THEN 'suggest: marketing_customer'
        WHEN tag_value LIKE 'page_%' THEN 'suggest: social_page'
        WHEN tag_value LIKE 'CK %' OR tag_value LIKE 'CHIẾT KHẤU%' THEN 'suggest: discount_deferred'
        ELSE 'review_needed'
    END as suggestion,
    CURRENT_TIMESTAMP as checked_at
FROM uncategorized
ORDER BY order_count DESC
