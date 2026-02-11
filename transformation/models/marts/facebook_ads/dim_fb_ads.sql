{{ config(
    enabled=false,
    materialized='table'
) }}

WITH ads AS (
    SELECT * FROM {{ ref('stg_fb_ads') }}
),
campaigns AS (
    SELECT * FROM {{ ref('stg_fb_campaigns') }}
),
ad_sets AS (
    SELECT * FROM {{ ref('stg_fb_ad_sets') }}
)

SELECT
    a.ad_id,
    a.ad_name,
    a.status AS ad_status,
    c.campaign_id,
    c.campaign_name,
    c.objective AS campaign_objective,
    as_set.adset_id,
    as_set.adset_name
FROM ads a
LEFT JOIN campaigns c ON a.campaign_id = c.campaign_id
LEFT JOIN ad_sets as_set ON a.adset_id = as_set.adset_id
