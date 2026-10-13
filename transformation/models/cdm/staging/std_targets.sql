{{ config(
    materialized='view',
    tags=['standard', 'targets']
) }}

-- Standard sales targets: thin pass-through over stg_targets.
-- Grain: 1/target_key.
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_targets') }}
)

SELECT
    target_key,
    target_code,
    cycle_start_date,
    cycle_end_date,
    cycle_type,
    branch_code,
    team_code,
    staff_email,
    sales_channel,
    product_sku,
    metric_code,
    target_val,
    description,
    ingest_method,
    'gsheet' AS source_system
FROM source_data
