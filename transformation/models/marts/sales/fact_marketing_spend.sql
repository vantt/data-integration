{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

WITH staged AS (
    SELECT * FROM {{ ref('stg_marketing_spend') }}
),

dim_channels AS (
    SELECT channel_key, source_id, location_id 
    FROM {{ ref('dim_channels') }}
)

SELECT
    s.spend_id as spend_key,
    
    -- Date Mapping
    cast(strftime(cast(s.date as date), '%Y%m%d') as integer) as date_key,
    
    -- Channel Mapping Logic (Direct)
    -- The ingestion layer now guarantees accurate source_id and location_id
    {{ dbt_utils.generate_surrogate_key([
        "cast(s.source_id as string)",
        "coalesce(cast(s.location_id as string), 'Unknown')" 
    ]) }} as channel_key,
    
    s.spend_code,
    s.campaign_id,
    
    -- Metrics
    s.spend_amount,
    s.clicks,
    s.impressions

FROM staged s
