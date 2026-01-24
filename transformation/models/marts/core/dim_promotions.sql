{{ config(
    tags=['mart', 'dim']
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}
),

unnested_promos AS (
    SELECT 
        order_id,
        unnest(from_json(discount_codes, '["JSON"]')) as promo_json
    FROM orders
    WHERE discount_codes IS NOT NULL
)

SELECT DISTINCT
    -- Surrogate Key
    md5(json_extract_string(promo_json, '$.code')) as promotion_key,
    
    -- Attributes
    json_extract_string(promo_json, '$.code') as promotion_code,
    try_cast(json_extract_string(promo_json, '$.amount') as DECIMAL(18,2)) as discount_amount,
    json_extract_string(promo_json, '$.type') as promotion_type

FROM unnested_promos
WHERE json_extract_string(promo_json, '$.code') IS NOT NULL
