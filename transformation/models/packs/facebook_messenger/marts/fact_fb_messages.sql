{{ config(
    enabled=false,
    materialized='table'
) }}

WITH source AS (
    SELECT * FROM {{ ref('stg_fb_messages') }}
)

SELECT
    message_id,
    thread_id,
    created_time,
    LENGTH(content) AS content_length_chars,
    sender_info
FROM source
