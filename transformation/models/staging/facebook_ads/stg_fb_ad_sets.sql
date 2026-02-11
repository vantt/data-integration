{{ config(
    enabled=false,
    materialized='view'
) }}

SELECT
    id AS adset_id,
    campaign_id,
    account_id,
    name AS adset_name,
    optimization_goal,
    billing_event,
    status
FROM {{ source('facebook_ads', 'ad_sets') }}
