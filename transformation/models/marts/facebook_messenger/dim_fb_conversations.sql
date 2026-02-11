{{ config(
    enabled=false,
    materialized='table'
) }}

WITH source AS (
    SELECT * FROM {{ ref('stg_fb_conversations') }}
)

SELECT
    thread_id,
    updated_time,
    message_count,
    snippet,
    participants -- Should be flattened in real implementation
FROM source
