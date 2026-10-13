{{ config(
    enabled=false,
    materialized='view'
) }}

SELECT
    id AS ad_id,
    adset_id,
    campaign_id,
    account_id,
    name AS ad_name,
    status,
    creative_id
FROM {{ source('facebook_ads', 'ads') }}
