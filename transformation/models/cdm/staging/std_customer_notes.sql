{{ config(
    materialized='view',
    tags=['standard', 'customers']
) }}

-- Standard customer notes: thin pass-through over stg_sapo_v2_customer_notes.
-- Grain: 1/(sapo_customer_id, note_id).
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_notes') }}
)

SELECT
    sapo_customer_id,
    note_id,
    content,
    created_on,
    account_id,
    'sapo_v2' AS source_system
FROM source_data
