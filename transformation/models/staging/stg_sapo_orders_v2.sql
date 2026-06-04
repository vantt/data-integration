{{ config(
    materialized='view',
    tags=['staging', 'orders']
) }}

-- =================================================================================================
-- STAGING: SAPO ORDERS
-- =================================================================================================
-- Purpose:
--   1. Enrichment joins (order sources, payment methods, branch locations).
--   2. All dedup (tech + biz) and JSON extraction already done in src_sapo_orders.
-- =================================================================================================

WITH orders AS (
    SELECT * FROM {{ ref('src_sapo_orders_v2') }}
),

mapped_tags AS (
    SELECT id, mapping_tag
    FROM {{ ref('ref_order_sources') }}
    WHERE mapping_tag IS NOT NULL
)

SELECT
    o.*,
    coalesce(cast(mt.id as string), cast(o.source_id as string)) as final_source_id,
    pm.name as payment_method_name,
    s.name as source_name,
    l.name as location_name

FROM orders o
LEFT JOIN mapped_tags mt
    ON o.tags IS NOT NULL
    AND o.tags LIKE '%' || mt.mapping_tag || '%'
LEFT JOIN {{ ref('ref_payment_methods') }} pm ON try_cast(o.payment_method_id as BIGINT) = pm.id
LEFT JOIN {{ ref('ref_order_sources') }} s ON coalesce(cast(mt.id as string), cast(o.source_id as string)) = cast(s.id as string)
LEFT JOIN {{ ref('ref_branch_locations') }} l ON try_cast(o.location_id as BIGINT) = l.id
