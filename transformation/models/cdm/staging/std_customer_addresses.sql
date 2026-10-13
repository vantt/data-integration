{{ config(
    materialized='view',
    tags=['standard', 'customers']
) }}

-- Standard customer addresses: thin pass-through over stg_sapo_v2_customer_addresses.
-- Grain: 1/(sapo_customer_id, address_id).
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_addresses') }}
)

SELECT
    sapo_customer_id,
    address_id,
    address1,
    address2,
    ward,
    district,
    city,
    province,
    zip,
    country,
    phone,
    company,
    first_name,
    last_name,
    'sapo_v2' AS source_system
FROM source_data
