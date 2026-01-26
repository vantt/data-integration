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
      AND discount_codes != '' 
      AND discount_codes != '[]'
      AND discount_codes != 'null'
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(["json_extract_string(promo_json, '$.code')"]) }} as promotion_key,
    
    -- Attributes
    json_extract_string(promo_json, '$.code') as promotion_code,
    try_cast(json_extract_string(promo_json, '$.amount') as DECIMAL(18,2)) as discount_amount,
    json_extract_string(promo_json, '$.type') as promotion_type

FROM unnested_promos
WHERE json_extract_string(promo_json, '$.code') IS NOT NULL

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as promotion_key,
    'Unknown' as promotion_code,
    0 as discount_amount,
    'Unknown' as promotion_type
