{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH source_definitions AS (
    SELECT * FROM {{ ref('ref_order_sources') }}
),

branch_locations AS (
    SELECT * FROM {{ ref('ref_branch_locations') }}
),

    -- 1. Specific Sources (Non-Generic)
    -- e.g. Facebook, Web -> Map 1-1 to Source
    specific_channels AS (
        SELECT
            cast(id as string) as source_id,
            null as location_id,
            name as channel_name,
            name as channel_code,
            platform_group,
            platform,
            channel_brand,
            market,
            customer_segment,
            status as is_active
        FROM source_definitions
        WHERE is_generic_source = false
    ),

    -- 2. Generic Sources expanded by Location (POS -> Stores)
    -- e.g. POS -> Map 1-N to Locations (Store A, Store B)
    generic_channels AS (
        SELECT
            cast(s.id as string) as source_id,
            cast(l.id as string) as location_id,
            l.name as channel_name,
            l.code as channel_code,
            s.platform_group,
            s.platform,
            s.channel_brand,
            s.market,
            s.customer_segment,
            s.status as is_active
        FROM source_definitions s
        CROSS JOIN branch_locations l
        WHERE s.is_generic_source = true
    ),

    unioned AS (
        SELECT * FROM specific_channels
        UNION ALL
        SELECT * FROM generic_channels
    )

SELECT
    -- Surrogate Key: Source + Location (0 if null)
    {{ dbt_utils.generate_surrogate_key([
        'source_id',
        "coalesce(location_id, 'Unknown')"
    ]) }} as channel_key,

    channel_name,
    channel_code,

    -- Channel classification
    CASE platform_group
        WHEN 'Ecom'   THEN 'Ecommerce'
        WHEN 'Social' THEN 'Ecommerce'
        WHEN 'Web'    THEN 'Ecommerce'
        WHEN 'Retail' THEN 'Offline'
        WHEN 'B2B'    THEN 'Offline'
        WHEN 'System' THEN 'Internal'
        WHEN 'CrossBorder' THEN 'Internal'
        ELSE 'Other'
    END as channel_category,
    platform_group,
    platform,
    channel_brand,
    market,
    customer_segment,
    platform_group NOT IN ('System', 'CrossBorder') as is_sales_channel,

    -- Lineage Links
    source_id,
    location_id,

    is_active

FROM unioned

UNION ALL

-- Unknown Member
SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as channel_key,
    'Unknown' as channel_name,
    'UNK' as channel_code,
    'Other' as channel_category,
    'Other' as platform_group,
    'Other' as platform,
    cast(null as varchar) as channel_brand,
    'Domestic' as market,
    'B2C' as customer_segment,
    false as is_sales_channel,
    cast(null as string) as source_id,
    cast(null as string) as location_id,
    true as is_active
