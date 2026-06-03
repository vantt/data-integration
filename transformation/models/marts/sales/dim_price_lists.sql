{{ config(
    tags=['mart', 'dim', 'products', 'prices'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- DIM: SAPO PRICE LISTS
-- =================================================================================================
-- Purpose:
--   Reference dimension for the 17 Sapo price lists.
--   Stable — changes only when Sapo admin adds/removes price lists.
--
-- Key flags:
--   is_cost = true  → GIANHAP only (import/cost price). Use as COGS proxy for ~10% of SKUs
--                     not in MISA. Verify: GIANHAP coverage on stg_sapo_variant_prices.
--   is_default = true → BANLE (standard retail price list).
--
-- Caveats:
--   - price_list.status = 'default' ≠ is_cost. GIANHAP has status='default' in Sapo but
--     is_cost=true — meaning it's the system-default cost list, not the retail default.
--     Both GIANHAP and BANLE have status='default' in raw payload.
--   - Source: variant_prices embedded inside product batch_sync parquet. The dedicated
--     price_list table (src_sapo_price_lists) is incomplete — only ~1 row in data lake.
--     Embedded source is more reliable.
-- =================================================================================================

SELECT DISTINCT
    price_list_id::BIGINT                                          AS price_list_id,
    price_list_code                                                AS code,
    price_list_name                                                AS name,
    'VND'                                                          AS currency_iso,
    is_cost_price                                                  AS is_cost,
    (price_list_code = 'BANLE')::BOOLEAN                          AS is_default
FROM {{ ref('std_variant_prices') }}
WHERE price_list_id IS NOT NULL
ORDER BY is_cost DESC, is_default DESC, code
