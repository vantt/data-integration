{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH orders_shipping_locs AS (
    SELECT DISTINCT
        shipping_province as province,
        shipping_district as district,
        shipping_ward as ward,
        shipping_country as country,
        MAX(updated_at) as last_seen_at
    FROM {{ ref('std_orders') }}
    WHERE shipping_province IS NOT NULL AND shipping_province != ''

    GROUP BY 1, 2, 3, 4
),

orders_billing_locs AS (
    SELECT DISTINCT
        billing_province as province,
        billing_district as district,
        billing_ward as ward,
        billing_country as country,
        MAX(updated_at) as last_seen_at
    FROM {{ ref('std_orders') }}
    WHERE billing_province IS NOT NULL AND billing_province != ''

    GROUP BY 1, 2, 3, 4
),

customers_locs AS (
    SELECT DISTINCT
        province,
        district,
        ward,
        country,
        MAX(updated_at) as last_seen_at
    FROM {{ ref('dim_customers') }}
    WHERE province IS NOT NULL AND province != '' AND province != 'Unknown'

    GROUP BY 1, 2, 3, 4
),

unioned_locs AS (
    SELECT * FROM orders_shipping_locs
    UNION ALL
    SELECT * FROM orders_billing_locs
    UNION ALL
    SELECT * FROM customers_locs
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(["trim(coalesce(province,''))", "trim(coalesce(district,''))", "trim(coalesce(ward,''))", "trim(coalesce(country, 'Vietnam'))"]) }} as geography_key,
    
    -- Hierarchy
    province,
    district,
    ward,
    coalesce(country, 'Vietnam') as country, -- Defaulting
    
    -- Metadata
    MAX(last_seen_at) as last_seen_at

FROM unioned_locs
WHERE 
    -- Prevent collision with the hardcoded 'Unknown' row below
    NOT (
        coalesce(province,'') = 'Unknown' AND 
        coalesce(district,'') = 'Unknown' AND 
        coalesce(ward,'') = 'Unknown'
    )
GROUP BY 1, 2, 3, 4, 5

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as geography_key,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as country,
    NULL as last_seen_at
