{{ config(
    materialized='view',
    tags=['staging', 'customers']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMERS
-- =================================================================================================
-- Purpose:
--   Reads from src_sapo_customers (already extracted & deduped).
--   Cleaning, formatting (phone, email, dates).
--   No JSON extraction needed — data is already flat from src_.
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_v2_customers') }}
)

SELECT
    entity_id,
    sapo_customer_id,
    customer_code,

    -- Personal info
    full_name,
    phone_number,
    email,
    status,

    -- Date of birth: consolidate birthday/dob
    coalesce(dob, birthday) as dob,
    sex,
    customer_group,

    -- Address
    city,
    province,
    district,
    ward,
    address1,
    country,

    -- Financials
    total_expense,
    orders_count,
    loyalty_point,
    debt,

    -- Timestamps
    created_on,
    modified_on,
    event_timestamp

FROM source_data
