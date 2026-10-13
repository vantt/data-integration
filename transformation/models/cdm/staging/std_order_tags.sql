{{ config(
    materialized='view',
    tags=['standard', 'orders']
) }}

-- Standard order tags (raw JSON array per order): thin pass-through over src_sapo_v2_orders.
-- Grain: 1/order revision row of the source; consumers unnest and dedupe.
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_v2_orders') }}
)

SELECT
    order_id,
    tags,
    'sapo_v2' AS source_system
FROM source_data
