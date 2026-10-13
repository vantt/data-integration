{{ config(
    materialized='view',
    tags=['standard', 'customers']
) }}

-- Standard customer tags: thin pass-through over stg_sapo_v2_customer_tags.
-- Grain: 1/(sapo_customer_id, tag_name).
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_tags') }}
)

SELECT
    sapo_customer_id,
    tag_name,
    'sapo_v2' AS source_system
FROM source_data
