{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH order_items AS (
    SELECT * FROM {{ ref('std_order_items') }}

),

brands AS (
    SELECT * FROM {{ ref('ref_brands') }}
),

ranked_products AS (
    -- Strategy: "Last Record Wins"
    -- Since we don't have a dedicated Product Sync yet, we extract products from Order Items.
    -- We use ROW_NUMBER() ordered by extracted_at DESC to always get the LATEST version of the product
    -- (e.g., if name or price changed, we get the new one).
    -- Todo: Update this when we have a dedicated Product Sync
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id
            ORDER BY extracted_at DESC
        ) as rn
    FROM order_items
    WHERE product_id IS NOT NULL
      AND product_name IS NOT NULL
)

SELECT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(["product_id || '-' || coalesce(variant_id, '')"]) }} as product_key,

    -- Natural Keys
    product_id,
    variant_id,
    sku,
    barcode,

    -- Attributes (Last Wins)
    product_name,
    variant_name,
    product_type,
    COALESCE(b.brand_name, p.vendor) as brand_name,
    b.brand_code,
    unit,
    weight_grams,
    unit_price as last_sold_price,

    -- Metadata
    extracted_at as last_seen_at

FROM ranked_products p
LEFT JOIN brands b ON UPPER(p.vendor) = UPPER(b.vendor_raw)
WHERE p.rn = 1

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as product_key,
    'Unknown' as product_id,
    'Unknown' as variant_id,
    'Unknown' as sku,
    'Unknown' as barcode,
    'Unknown' as product_name,
    'Unknown' as variant_name,
    'Unknown' as product_type,
    'Unknown' as brand_name,
    cast(null as varchar) as brand_code,
    'Unknown' as unit,
    0 as weight_grams,
    0 as last_sold_price,
    NULL as last_seen_at
