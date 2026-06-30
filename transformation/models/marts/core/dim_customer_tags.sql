{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CUSTOMER TAGS
-- =================================================================================================
-- Purpose:
--   One row per (customer_key, tag_name). Joins stg_sapo_v2_customer_tags with
--   dim_customers_base to expose customer_key as the stable warehouse FK.
-- Grain: customer × tag
-- =================================================================================================

WITH tags AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_tags') }}
),

customers AS (
    SELECT customer_key, customer_id
    FROM {{ ref('dim_customers_base') }}
    WHERE customer_id != 'Unknown'
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['c.customer_key', 't.tag_name']) }} AS tag_key,
    c.customer_key,
    CAST(t.sapo_customer_id AS VARCHAR) AS sapo_customer_id,
    t.tag_name
FROM tags t
INNER JOIN customers c ON CAST(t.sapo_customer_id AS VARCHAR) = CAST(c.customer_id AS VARCHAR)
