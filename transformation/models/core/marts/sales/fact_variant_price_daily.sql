{{ config(
    tags=['mart', 'fact', 'products', 'prices', 'history'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: VARIANT PRICE DAILY (price history from the nightly capture)
-- =================================================================================================
-- Grain: 1 row per (variant_id, price_list_id, as_of_date).
-- as_of_date: ICT day the capture stands for (macro history_as_of_date, var
--   history_day_cutoff_hour): the 03:01 nightly capture of D+1 records the end of day D.
--   Several captures for one day: the latest captured_at wins (a re-run is idempotent).
-- Source: daily_capture observations only (std_variant_price_observations), so a day exists only
--   when a capture ran for it: a missed night is a missing day, never filled in.
-- Zero prices are kept with is_configured = false (fact_variant_prices_snapshot drops them).
-- Source-provided values only: no margin column (margin calculations belong to the finance pack).
-- Rebuilt in full from raw on every build (rolling parquet; history lives in raw).
-- =================================================================================================

WITH captures AS (
    SELECT
        variant_id::BIGINT              AS variant_id,
        price_list_id::BIGINT           AS price_list_id,
        {{ history_as_of_date('observed_at') }} AS as_of_date,
        sku,
        product_id::BIGINT              AS product_id,
        price_list_code,
        price_list_name,
        is_cost_price                   AS is_cost,
        price_value::DECIMAL(18,2)      AS price_value,
        price_incl_tax::DECIMAL(18,2)   AS price_incl_tax,
        observed_at                     AS captured_at,
        observation_ref
    FROM {{ ref('std_variant_price_observations') }}
    WHERE evidence_source = 'daily_capture'
      AND variant_id IS NOT NULL
      AND price_list_id IS NOT NULL
)

SELECT
    variant_id,
    price_list_id,
    as_of_date,
    sku,
    product_id,
    price_list_code,
    price_list_name,
    is_cost,
    price_value,
    price_incl_tax,
    COALESCE(price_value, 0) > 0        AS is_configured,
    captured_at
FROM captures
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY variant_id, price_list_id, as_of_date
    ORDER BY captured_at DESC, observation_ref DESC
) = 1
