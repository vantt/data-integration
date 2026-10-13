{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CUSTOMER ADDRESSES (all address slots)
-- =================================================================================================
-- Purpose:
--   One row per (customer_key, address_id). Captures ALL Sapo address slots per customer.
--   Primary address scalars (address1/province/district/ward/zip) are also in dim_customers_base
--   as addresses[0]; this bridge table holds the full multi-address set.
-- Grain: customer × address
-- =================================================================================================

WITH addresses AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_addresses') }}
),

customers AS (
    SELECT customer_key, customer_id
    FROM {{ ref('dim_customers_base') }}
    WHERE customer_id != 'Unknown'
)

SELECT
    c.customer_key,
    CAST(a.sapo_customer_id AS VARCHAR) AS sapo_customer_id,
    a.address_id,
    a.address1,
    a.address2,
    a.ward,
    a.district,
    a.city,
    a.province,
    a.zip,
    a.country,
    a.phone,
    a.company,
    a.first_name,
    a.last_name
FROM addresses a
INNER JOIN customers c ON CAST(a.sapo_customer_id AS VARCHAR) = CAST(c.customer_id AS VARCHAR)
