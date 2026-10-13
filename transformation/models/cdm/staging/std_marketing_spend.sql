{{ config(
    materialized='view',
    tags=['standard', 'marketing']
) }}

-- Standard marketing spend: thin pass-through over stg_marketing_spend.
-- Grain: 1/spend_id.
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_marketing_spend') }}
)

SELECT
    spend_id,
    date,
    spend_code,
    campaign_id,
    spend_amount,
    clicks,
    impressions,
    ingest_method,
    source_id,
    location_id,
    year,
    month,
    'gsheet' AS source_system
FROM source_data
