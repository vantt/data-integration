{{ config(
    enabled=false,
    materialized='view'
) }}

SELECT
    id AS thread_id,
    updated_time,
    message_count,
    snippet,
    link,
    -- Extracting Page ID and User ID would likely require parsing the participants field
    -- This is a simplified extraction
    participants
FROM {{ source('facebook_messenger', 'conversations') }}
