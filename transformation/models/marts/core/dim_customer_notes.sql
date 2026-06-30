{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CUSTOMER NOTES (Sapo-sourced)
-- =================================================================================================
-- Purpose:
--   One row per (customer_key, note_id). Sapo internal memos attached to customer accounts.
--   Distinct from crm_note (CRM staff notes in crm.db).
-- Grain: customer × note
-- =================================================================================================

WITH notes AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customer_notes') }}
),

customers AS (
    SELECT customer_key, customer_id
    FROM {{ ref('dim_customers_base') }}
    WHERE customer_id != 'Unknown'
)

SELECT
    c.customer_key,
    CAST(n.sapo_customer_id AS VARCHAR) AS sapo_customer_id,
    n.note_id,
    n.content,
    try_cast(n.created_on AS TIMESTAMPTZ) AS created_at,
    n.account_id
FROM notes n
INNER JOIN customers c ON CAST(n.sapo_customer_id AS VARCHAR) = CAST(c.customer_id AS VARCHAR)
