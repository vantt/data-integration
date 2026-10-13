{{ config(
    tags=['stg', 'marketing'],
    location="{{ get_rolling_location() }}"
) }}

WITH raw_data AS (
    SELECT * 
    FROM {{ source('gsheet_raw', 'marketing_spend_raw') }}
)

SELECT
    -- Generate Surrogate Key based on relevant business keys
    -- Assuming (date + spend_code + campaign_id) is unique enough for a spending entry
    {{ dbt_utils.generate_surrogate_key(['date', 'spend_code', 'campaign_id']) }} as spend_id,
    
    date,
    spend_code,
    campaign_id,
    cast(spend_amount as decimal(15,2)) as spend_amount,
    cast(clicks as integer) as clicks,
    cast(impressions as integer) as impressions,
    
    ingest_method,
    
    -- Channel Reference (Direct from Ingestion)
    cast(source_id as VARCHAR) as source_id,
    cast(location_id as VARCHAR) as location_id,
    
    -- Metadata
    year,
    month

FROM raw_data
