{{ config(
    tags=['mart', 'fact', '{SOURCE}'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- FACT: FACT_{PROCESS_UPPER}
-- =============================================================================
-- Pattern:
--   1. Đọc từ std_{entity} (golden layer, KHÔNG đọc src_/stg_ trực tiếp)
--   2. FK join với dimensions qua surrogate key
--   3. COALESCE về Unknown key nếu missing (không drop fact row)
--   4. Generate date_key/time_key cho dim_date/dim_time joins
-- =============================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('std_{process}') }}
),

-- Join với dimensions để lấy surrogate keys
enriched AS (
    SELECT
        s.{process}_id,

        -- Dimension FKs với Unknown fallback
        COALESCE(
            dc.customer_key,
            {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ) AS customer_key,

        COALESCE(
            dp.product_key,
            {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ) AS product_key,

        -- TODO: thêm các dimension FKs khác

        -- Date/time keys (integer cho performance)
        COALESCE(
            CAST(strftime(s.created_at, '%Y%m%d') AS INTEGER),
            19000101
        ) AS date_key,
        (EXTRACT(hour FROM s.created_at) * 100) + EXTRACT(minute FROM s.created_at) AS time_key,

        -- Measures
        s.total_amount,
        s.total_discount,
        s.total_tax,
        s.quantity,

        -- Degenerate dimensions (low cardinality, không worth tạo dim riêng)
        s.status,
        s.channel_name,

        -- Audit
        s.created_at,
        s.updated_at

    FROM source_data s
    LEFT JOIN {{ ref('dim_customers') }}  dc ON s.customer_id = dc.customer_id
    LEFT JOIN {{ ref('dim_products') }}   dp ON s.product_id  = dp.product_id
    -- TODO: thêm joins khác
)

SELECT * FROM enriched
