{{ config(
    enabled=false,
    materialized='view'
) }}

SELECT
    id AS message_id,
    conversation_id AS thread_id, -- assuming dlt links this, or needs join
    created_time,
    message AS content,
    "from" AS sender_info,
    "to" AS recipient_info
FROM {{ source('facebook_messenger', 'messages') }}
