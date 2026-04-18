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

    -- Parent rows are those whose name prefixes other rows' names with " - "
    -- (e.g. "Shopee" is parent of "Shopee - JPC OFFICIAL"). When materialized into
    -- dim_channels, parent rows get " (Unspecified)" suffix so users can tell
    -- orders mapped to a specific storefront from orders still tagged with the
    -- generic Sapo source. Leaf platforms with no children (Facebook, Zalo, Web,
    -- Telesale...) are not suffixed.
    --
    -- Name-based detection: seed properties.yml declares id INTEGER, and DuckDB's
    -- integer parser strips underscores as digit separators, so composite ids
    -- like '3988158_1' lose the underscore at load time — id-based LIKE match
    -- cannot detect parent/child relationships. Names stay intact.
    parents_with_children AS (
        SELECT DISTINCT p.id as parent_id
        FROM source_definitions p
        WHERE EXISTS (
            SELECT 1 FROM source_definitions c
            WHERE c.name LIKE p.name || ' - %'
              AND c.id <> p.id
        )
    ),

    -- 1. Specific Sources (Non-Generic)
    -- e.g. Facebook, Web -> Map 1-1 to Source. Marketplace parents get "(Unspecified)"
    -- suffix when their sibling composite children exist in the seed.
    specific_channels AS (
        SELECT
            cast(s.id as string) as source_id,
            null as location_id,
            CASE
                WHEN pwc.parent_id IS NOT NULL THEN s.name || ' (Unspecified)'
                ELSE s.name
            END as channel_name,
            s.name as channel_code,
            s.channel_format,
            s.platform,
            s.channel_brand,
            s.market,
            s.source_type,
            s.status as is_active
        FROM source_definitions s
        LEFT JOIN parents_with_children pwc
            ON s.id = pwc.parent_id
        WHERE s.is_generic_source = false
    ),

    -- 2. Generic Sources expanded by Location (POS -> Stores)
    -- e.g. POS -> Map 1-N to Locations. channel_name prefixed with platform so values
    -- are unambiguous across platforms (e.g. "POS - 16 Trương Định").
    generic_channels AS (
        SELECT
            cast(s.id as string) as source_id,
            cast(l.id as string) as location_id,
            s.platform || ' - ' || l.name as channel_name,
            l.code as channel_code,
            s.channel_format,
            s.platform,
            s.channel_brand,
            s.market,
            s.source_type,
            s.status as is_active
        FROM source_definitions s
        CROSS JOIN branch_locations l
        WHERE s.is_generic_source = true
    ),

    -- 3. Generic Sources with Unknown Location (fallback for unrecognized location_ids)
    generic_unknown AS (
        SELECT
            cast(s.id as string) as source_id,
            null as location_id,
            s.platform || ' - Unknown Location' as channel_name,
            s.name as channel_code,
            s.channel_format,
            s.platform,
            s.channel_brand,
            s.market,
            s.source_type,
            s.status as is_active
        FROM source_definitions s
        WHERE s.is_generic_source = true
    ),

    unioned AS (
        SELECT * FROM specific_channels
        UNION ALL
        SELECT * FROM generic_channels
        UNION ALL
        SELECT * FROM generic_unknown
    )

SELECT
    -- Surrogate Key: Source + Location (0 if null)
    {{ dbt_utils.generate_surrogate_key([
        'source_id',
        "coalesce(location_id, 'Unknown')"
    ]) }} as channel_key,

    channel_name,
    channel_code,

    -- Tier 1: channel_category (Online-Ecommerce / Offline / Internal)
    CASE channel_format
        WHEN 'Marketplace' THEN 'Online-Ecommerce'
        WHEN 'Social'      THEN 'Online-Ecommerce'
        WHEN 'Web'         THEN 'Online-Ecommerce'
        WHEN 'Retail'      THEN 'Offline'
        WHEN 'B2B'         THEN 'Offline'
        WHEN 'Direct'      THEN 'Offline'
        WHEN 'System'      THEN 'Internal'
        WHEN 'CrossBorder Fulfillment' THEN 'Internal'
        ELSE 'Internal'
    END as channel_category,

    -- Tier 2: channel_format (Marketplace / Social / Web / Retail / B2B / Direct / System / CrossBorder Fulfillment / Other)
    channel_format,

    -- Tier 3: platform
    platform,

    channel_brand,
    market,
    source_type,

    -- Real sales channel flag: excludes internal/system and non-sales fulfillment.
    channel_format NOT IN ('System', 'CrossBorder Fulfillment', 'Other') as is_sales_channel,

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
    'Internal' as channel_category,
    'Other' as channel_format,
    'Other' as platform,
    cast(null as varchar) as channel_brand,
    'Domestic' as market,
    'channel' as source_type,
    false as is_sales_channel,
    cast(null as string) as source_id,
    cast(null as string) as location_id,
    true as is_active
