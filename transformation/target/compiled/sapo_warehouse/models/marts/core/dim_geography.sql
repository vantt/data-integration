

WITH orders_locs AS (
    SELECT DISTINCT
        shipping_province as province,
        shipping_district as district,
        shipping_ward as ward,
        shipping_country as country
    FROM "data_integration2"."main_staging"."std_orders"
    WHERE shipping_province IS NOT NULL AND shipping_province != ''
),

customers_locs AS (
    SELECT DISTINCT
        province,
        district,
        ward,
        country
    FROM "data_integration2"."main_marts"."dim_customers"
    WHERE province IS NOT NULL AND province != '' AND province != 'Unknown'
),

unioned_locs AS (
    SELECT * FROM orders_locs
    UNION
    SELECT * FROM customers_locs
)

SELECT DISTINCT
    -- Surrogate Key
    md5(
        coalesce(province,'') || '-' || 
        coalesce(district,'') || '-' || 
        coalesce(ward,'')
    ) as geography_key,
    
    -- Hierarchy
    province,
    district,
    ward,
    coalesce(country, 'Vietnam') as country -- Defaulting

FROM unioned_locs
WHERE 
    -- Prevent collision with the hardcoded 'Unknown' row below
    NOT (
        coalesce(province,'') = 'Unknown' AND 
        coalesce(district,'') = 'Unknown' AND 
        coalesce(ward,'') = 'Unknown'
    )

UNION ALL

SELECT
    md5('Unknown') as geography_key,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as country