{{ config(
    materialized='view',
    tags=['standard', 'orders']
) }}

-- Standard order tags (raw JSON array per order): thin pass-through over src_sapo_v2_orders.
-- Grain: 1/order revision row of the source; consumers unnest and dedupe.
-- Projects only order_id and tags (the one consumer, int_order_tags, needs no other column;
-- the source is wide), with the source's names and types, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_v2_orders') }}
)

SELECT
    order_id,
    tags,
    'sapo_v2' AS source_system
FROM source_data
