{{ config(
    enabled=false,
    materialized='view'
) }}

SELECT
    id AS campaign_id,
    account_id,
    name AS campaign_name,
    objective,
    status,
    start_time,
    created_time
FROM {{ source('facebook_ads', 'campaigns') }}
