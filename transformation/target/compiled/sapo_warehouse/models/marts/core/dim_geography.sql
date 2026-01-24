

WITH orders AS (
    SELECT * FROM "data_integration2"."main_staging"."std_orders"
),

distinct_locs AS (
    SELECT DISTINCT
        json_extract_string(shipping_address, '$.province') as province,
        json_extract_string(shipping_address, '$.district') as district,
        json_extract_string(shipping_address, '$.ward') as ward,
        json_extract_string(shipping_address, '$.country') as country
    FROM orders
    WHERE shipping_address IS NOT NULL
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

FROM distinct_locs
WHERE 
    (province IS NOT NULL AND province != '') 
    AND (district IS NOT NULL AND district != '')
    -- Prevent collision with the hardcoded 'Unknown' row below
    AND NOT (
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