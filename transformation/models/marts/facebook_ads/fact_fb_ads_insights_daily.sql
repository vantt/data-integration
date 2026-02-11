{{ config(
    enabled=false,
    materialized='table'
) }}

WITH insights AS (
    SELECT
        date_start AS date,
        ad_id,
        adset_id,
        campaign_id,
        account_id,
        spend,
        impressions,
        clicks,
        reach,
        frequency
    FROM {{ source('facebook_ads', 'insights') }}
)

SELECT * FROM insights
