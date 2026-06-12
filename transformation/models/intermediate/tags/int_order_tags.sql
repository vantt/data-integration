{{ config(
    materialized='view',
    tags=['intermediate', 'orders', 'tags']
) }}

-- =============================================================================
-- INTERMEDIATE: ORDER TAGS
-- =============================================================================
-- Purpose: Unnest order tags JSON array and categorize each tag
-- Input: src_sapo_orders.tags (JSON string array)
-- Output: One row per order-tag pair with semantic category
-- Docs: transformation/docs/TAG_HANDLING.md
-- =============================================================================

WITH raw_tags AS (
    SELECT
        order_id,
        TRIM(REPLACE(tag.value::VARCHAR, '"', '')) as tag_value
    -- T0.4 DECISION (2026-06-03): reads src_sapo_orders directly for $.tags. Deferred to v3 work (option a) — when v3 arrives, expose tags via std_orders or add a v3 path. Gated by Q1-Q5.
    FROM {{ ref('src_sapo_v2_orders') }},
    LATERAL UNNEST(
        CASE
            WHEN tags IS NOT NULL AND tags NOT IN ('', '[]')
            THEN json_extract(tags, '$[*]')
            ELSE NULL
        END
    ) as tag(value)
    WHERE tags IS NOT NULL
      AND tags NOT IN ('', '[]')
),

category_mappings AS (
    SELECT
        pattern,
        category,
        match_type,
        priority
    FROM {{ ref('ref_tag_categories') }}
),

matched AS (
    SELECT
        t.order_id,
        t.tag_value,
        m.category as tag_category,
        m.priority,
        ROW_NUMBER() OVER (
            PARTITION BY t.order_id, t.tag_value
            ORDER BY m.priority ASC NULLS LAST  -- lower priority number = higher importance
        ) as rn
    FROM raw_tags t
    LEFT JOIN category_mappings m
        ON (m.match_type = 'exact' AND t.tag_value = m.pattern)
        OR (m.match_type = 'prefix' AND t.tag_value LIKE m.pattern)
        OR (m.match_type = 'contains' AND t.tag_value LIKE m.pattern)
)

SELECT
    order_id,
    tag_value,
    COALESCE(tag_category, 'uncategorized') as tag_category
FROM matched
WHERE rn = 1 OR rn IS NULL
