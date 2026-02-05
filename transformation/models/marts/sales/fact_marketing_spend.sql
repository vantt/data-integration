{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

WITH staged AS (
    SELECT * FROM {{ ref('stg_marketing_spend') }}
),

map_channels AS (
    SELECT * FROM {{ ref('ref_marketing_spend_map') }}
),

dim_channels AS (
    SELECT channel_key, source_id, location_id 
    FROM {{ ref('dim_channels') }}
)

SELECT
    s.spend_id as spend_key,
    
    -- Date Mapping
    cast(strftime(cast(s.date as date), '%Y%m%d') as integer) as date_key,
    
    -- Channel Mapping Logic
    -- 1. Get Source/Location from ref_marketing_channels using spend_code
    -- 2. Generate same Hash Key as dim_channels
    {{ dbt_utils.generate_surrogate_key([
        "coalesce(cast(mc.map_id as string), 'Unknown')", -- source_id (if map_type=SOURCE)
        "CASE WHEN mc.map_type = 'LOCATION' THEN cast(mc.map_id as string) ELSE 'Unknown' END" -- location_id
    ]) }} as channel_key,
    
    s.spend_code,
    s.campaign_id,
    
    -- Metrics
    s.spend_amount,
    s.clicks,
    s.impressions

FROM staged s
LEFT JOIN map_channels mc ON s.spend_code = mc.spend_code
