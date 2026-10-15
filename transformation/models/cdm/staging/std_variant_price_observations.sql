{{ config(
    materialized='view',
    tags=['standard', 'products', 'prices', 'history']
) }}

-- =================================================================================================
-- STANDARD: VARIANT PRICE OBSERVATIONS
-- =================================================================================================
-- Every observed price of a (variant, price list), from two kinds of evidence:
--   daily_capture        - nightly full capture (stg_sapo_v2_variant_price_captures), observed_at =
--                          captured_at; observation_ref = capture_run_id
--   sapo_product_version - each product version ever loaded (stg_sapo_v2_variant_price_versions),
--                          observed_at = version event_timestamp; observation_ref = _dlt_load_id
-- Grain: one row per observation (several identical rows are possible for product versions that
-- were loaded more than once; the history marts collapse them).
-- =================================================================================================

SELECT
    variant_id,
    product_id,
    sku,
    price_list_id,
    price_list_name,
    price_list_code,
    is_cost_price,
    price_value,
    price_incl_tax,
    captured_at                       AS observed_at,
    'daily_capture'                   AS evidence_source,
    capture_run_id                    AS observation_ref,
    'sapo_v2'                         AS source_system,
    'v2'                              AS source_version
FROM {{ ref('stg_sapo_v2_variant_price_captures') }}

UNION ALL

SELECT
    variant_id,
    product_id,
    sku,
    price_list_id,
    price_list_name,
    price_list_code,
    is_cost_price,
    price_value,
    price_incl_tax,
    observed_at,
    'sapo_product_version'            AS evidence_source,
    _dlt_load_id                      AS observation_ref,
    'sapo_v2'                         AS source_system,
    'v2'                              AS source_version
FROM {{ ref('stg_sapo_v2_variant_price_versions') }}
