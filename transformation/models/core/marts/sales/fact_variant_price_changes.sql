{{ config(
    tags=['mart', 'fact', 'products', 'prices', 'history'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: VARIANT PRICE CHANGES (price intervals, SCD type 2)
-- =================================================================================================
-- Grain: 1 row per (variant_id, price_list_id, valid_from_at): a run of consecutive observations
-- with the same (price_value, price_incl_tax).
-- Evidence (std_variant_price_observations):
--   - sapo_product_version: every product version loaded into raw (batch since 28/05/2026,
--     history_log for some products since 03/2026). Intervals that start before the first full
--     load are inferred from the product's modified_on. Price changes Sapo made without moving
--     modified_on are invisible here.
--   - daily_capture: the nightly full capture (since 15/10/2026), which sees every change.
--   Several observations at the same instant: daily_capture wins.
-- Dates:
--   valid_from_date = as_of_date of the first observation for a capture (history_as_of_date), the
--     ICT calendar date for a product version.
--   valid_to_date = day before the next interval's valid_from_date; NULL while current. A price
--     replaced on the same day it started has valid_to_date < valid_from_date: it never held at the
--     end of a day, so "D BETWEEN valid_from_date AND valid_to_date" (as of end of day D) skips it.
--   valid_to_at = valid_from_at of the next interval (exclusive).
-- A pair missing from the latest capture (variant or price list removed in Sapo) is closed at its
-- last observation: valid_to_at = last_observed_at, valid_to_date = its date, is_current = false.
-- previous_price_value / price_change_pct compare with the previous interval (not a margin).
-- Rebuilt in full from raw on every build.
-- =================================================================================================

WITH obs AS (
    SELECT
        variant_id::BIGINT              AS variant_id,
        price_list_id::BIGINT           AS price_list_id,
        sku,
        product_id::BIGINT              AS product_id,
        price_list_code,
        price_list_name,
        is_cost_price                   AS is_cost,
        price_value::DECIMAL(18,2)      AS price_value,
        price_incl_tax::DECIMAL(18,2)   AS price_incl_tax,
        observed_at,
        CASE
            WHEN evidence_source = 'daily_capture' THEN {{ history_as_of_date('observed_at') }}
            ELSE CAST(timezone('Asia/Ho_Chi_Minh', observed_at) AS DATE)
        END                             AS observed_date,
        evidence_source,
        observation_ref
    FROM {{ ref('std_variant_price_observations') }}
    WHERE variant_id IS NOT NULL
      AND price_list_id IS NOT NULL
      AND observed_at IS NOT NULL
),

-- One observation per pair and instant (product versions loaded several times are identical)
obs_dedup AS (
    SELECT *
    FROM obs
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY variant_id, price_list_id, observed_at
        ORDER BY CASE evidence_source WHEN 'daily_capture' THEN 0 ELSE 1 END, observation_ref DESC
    ) = 1
),

flagged AS (
    SELECT
        *,
        CASE
            WHEN LAG(observed_at) OVER w IS NOT NULL
             AND LAG(price_value) OVER w IS NOT DISTINCT FROM price_value
             AND LAG(price_incl_tax) OVER w IS NOT DISTINCT FROM price_incl_tax
            THEN 0 ELSE 1
        END AS starts_interval
    FROM obs_dedup
    WINDOW w AS (PARTITION BY variant_id, price_list_id ORDER BY observed_at)
),

numbered AS (
    SELECT
        *,
        SUM(starts_interval) OVER (
            PARTITION BY variant_id, price_list_id ORDER BY observed_at
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS interval_no
    FROM flagged
),

intervals AS (
    SELECT
        variant_id,
        price_list_id,
        interval_no,
        MIN(observed_at)                            AS valid_from_at,
        arg_min(observed_date, observed_at)         AS valid_from_date,
        MAX(observed_at)                            AS last_observed_at,
        arg_max(observed_date, observed_at)         AS last_observed_date,
        arg_min(evidence_source, observed_at)       AS evidence_source,
        arg_min(price_value, observed_at)           AS price_value,
        arg_min(price_incl_tax, observed_at)        AS price_incl_tax,
        arg_max(sku, observed_at)                   AS sku,
        arg_max(product_id, observed_at)            AS product_id,
        arg_max(price_list_code, observed_at)       AS price_list_code,
        arg_max(price_list_name, observed_at)       AS price_list_name,
        arg_max(is_cost, observed_at)               AS is_cost
    FROM numbered
    GROUP BY variant_id, price_list_id, interval_no
),

latest_capture AS (
    SELECT MAX(observed_at) AS latest_capture_at
    FROM obs
    WHERE evidence_source = 'daily_capture'
),

chained AS (
    SELECT
        i.*,
        LEAD(i.valid_from_at)   OVER w              AS next_valid_from_at,
        LEAD(i.valid_from_date) OVER w              AS next_valid_from_date,
        LAG(i.price_value)      OVER w              AS previous_price_value,
        lc.latest_capture_at
    FROM intervals i
    CROSS JOIN latest_capture lc
    WINDOW w AS (PARTITION BY i.variant_id, i.price_list_id ORDER BY i.valid_from_at)
),

closed AS (
    SELECT
        *,
        next_valid_from_at IS NULL
            AND latest_capture_at IS NOT NULL
            AND last_observed_at < latest_capture_at  AS is_removed
    FROM chained
)

SELECT
    variant_id,
    price_list_id,
    valid_from_at,
    valid_from_date,
    CASE
        WHEN next_valid_from_at IS NOT NULL THEN next_valid_from_at
        WHEN is_removed THEN last_observed_at
    END                                             AS valid_to_at,
    CASE
        WHEN next_valid_from_at IS NOT NULL THEN next_valid_from_date - 1
        WHEN is_removed THEN last_observed_date
    END                                             AS valid_to_date,
    sku,
    product_id,
    price_list_code,
    price_list_name,
    is_cost,
    price_value,
    price_incl_tax,
    COALESCE(price_value, 0) > 0                    AS is_configured,
    previous_price_value,
    CASE
        WHEN previous_price_value > 0
        THEN ROUND((price_value - previous_price_value) * 100.0 / previous_price_value, 2)
    END                                             AS price_change_pct,
    evidence_source,
    last_observed_at,
    next_valid_from_at IS NULL AND NOT is_removed  AS is_current
FROM closed
