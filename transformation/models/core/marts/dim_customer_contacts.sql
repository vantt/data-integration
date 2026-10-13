{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CUSTOMER CONTACTS (B2B contact persons)
-- =================================================================================================
-- Purpose:
--   One row per (customer_key, contact_id). B2B contact persons attached to wholesale/partner
--   customer accounts in Sapo (name, phone, email, position).
-- Grain: customer × contact person
-- =================================================================================================

WITH contacts AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_contacts') }}
),

customers AS (
    SELECT customer_key, customer_id
    FROM {{ ref('dim_customers_base') }}
    WHERE customer_id != 'Unknown'
)

SELECT
    c.customer_key,
    CAST(ct.sapo_customer_id AS VARCHAR) AS sapo_customer_id,
    ct.contact_id,
    ct.contact_name,
    ct.phone,
    ct.email,
    ct.position,
    ct.organization
FROM contacts ct
INNER JOIN customers c ON CAST(ct.sapo_customer_id AS VARCHAR) = CAST(c.customer_id AS VARCHAR)
